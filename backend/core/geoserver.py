"""GeoServer REST integration for harvested files and WMS 1.3.0 URLs."""

import asyncio
import errno
import hashlib
import logging
import math
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote

import httpx

from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.geoserver")


def _mirror_dir_on_source_mount(source: Path, directory: Path) -> Path:
    """Find the mirror through the same Docker host-home bind mount as the source."""
    home = Path("/host_home")
    if not source.is_relative_to(home):
        return directory
    try:
        # Linux disallows hard links across two bind mounts, even on the same disk.
        mounts = {}
        for line in Path("/proc/self/mountinfo").read_text().splitlines():
            _, _, device, root, mountpoint, *_ = line.split()
            mountpoint = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), mountpoint)
            if mountpoint in {str(home), str(directory)}:
                root = re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), root)
                mounts[Path(mountpoint)] = (device, Path(root))
        if home in mounts and directory in mounts:
            home_device, home_root = mounts[home]
            mirror_device, mirror_root = mounts[directory]
            if home_device == mirror_device and mirror_root.is_relative_to(home_root):
                alias = home / mirror_root.relative_to(home_root)
                if alias.samefile(directory):
                    return alias
    except OSError:
        pass
    return directory


class GeoServerManager:
    """Mirror downloaded files into GeoServer-visible storage and publish GeoTIFFs."""

    def __init__(self) -> None:
        self._workspace_lock = asyncio.Lock()
        self._style_lock = asyncio.Lock()

    @property
    def rest_url(self) -> str:
        return settings.geoserver_rest_url.rstrip("/")

    @property
    def wms_url(self) -> str:
        return f"{settings.geoserver_public_url.rstrip('/')}/wms"

    @property
    def internal_wms_url(self) -> str:
        return f"{self.rest_url}/wms"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=(settings.geoserver_admin_user, settings.geoserver_admin_password),
            timeout=httpx.Timeout(45.0, connect=5.0),
        )

    @staticmethod
    def _safe_name(value: str) -> str:
        safe = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").lower()
        if not safe or not safe[0].isalpha():
            safe = f"layer_{safe}"
        return safe[:48]

    def _server_file_path(self, source: Path) -> str:
        source = source.resolve()
        downloads_root = settings.downloads_dir.resolve()
        try:
            relative = source.relative_to(downloads_root)
            return f"{settings.geoserver_downloads_mount.rstrip('/')}/{relative.as_posix()}"
        except ValueError:
            pass

        settings.geoserver_files_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(str(source).encode("utf-8")).hexdigest()[:12]
        target_name = f"{digest}_{source.name}"
        target_dir = _mirror_dir_on_source_mount(source, settings.geoserver_files_dir.resolve())
        target = target_dir / target_name
        source_stat = source.stat()
        target_stat = target.stat() if target.exists() else None
        if target_stat is None or not source.samefile(target):
            # Publish atomically, also when an export replaces a same-sized scene.
            temporary = target.with_name(f".{target_name}.{uuid.uuid4().hex}.tmp")
            try:
                try:
                    temporary.hardlink_to(source)
                except OSError as exc:
                    if exc.errno not in {errno.EXDEV, errno.EPERM, errno.ENOTSUP, errno.EMLINK, errno.EACCES, errno.ENOSYS}:
                        raise
                    if (target_stat is not None and target_stat.st_size == source_stat.st_size
                            and target_stat.st_mtime_ns == source_stat.st_mtime_ns):
                        return f"{settings.geoserver_external_mount.rstrip('/')}/{target_name}"
                    shutil.copy2(source, temporary)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        return f"{settings.geoserver_external_mount.rstrip('/')}/{target_name}"

    async def _ensure_workspace(self, client: httpx.AsyncClient) -> None:
        workspace = quote(settings.geoserver_workspace, safe="")
        url = f"{self.rest_url}/rest/workspaces/{workspace}.json"
        async with self._workspace_lock:
            response = await client.get(url)
            if response.status_code == 200:
                return
            if response.status_code != 404:
                response.raise_for_status()
            created = await client.post(
                f"{self.rest_url}/rest/workspaces",
                json={"workspace": {"name": settings.geoserver_workspace}},
            )
            if created.status_code not in (201, 409):
                created.raise_for_status()

    async def _resolve_store_layer_name(
        self,
        client: httpx.AsyncClient,
        workspace: str,
        store_name: str,
        fallback_name: str,
    ) -> str:
        """Read the actual published coverage/layer name created by GeoServer for a store."""
        cov_url = (
            f"{self.rest_url}/rest/workspaces/{workspace}/coveragestores/"
            f"{quote(store_name, safe='')}/coverages.json"
        )
        cov_resp = await client.get(cov_url)
        if cov_resp.status_code != 200:
            return fallback_name
        try:
            payload = cov_resp.json()
        except ValueError:
            return fallback_name
        raw_coverages = (payload.get("coverages") or {}).get("coverage") or []
        if isinstance(raw_coverages, dict):
            raw_coverages = [raw_coverages]
        if isinstance(raw_coverages, list):
            for item in raw_coverages:
                if isinstance(item, dict) and item.get("name"):
                    return str(item["name"])
        return fallback_name

    async def ingest(self, path: Path) -> Dict[str, Any]:
        """Store any completed download in GeoServer-visible storage and publish GeoTIFFs."""
        source = Path(path).expanduser().resolve()
        if not settings.geoserver_enabled:
            return {"enabled": False, "stored": False, "published": False}
        if ".staging" in source.parts:
            return {"enabled": True, "stored": False, "published": False, "skipped": "staging"}
        if not source.is_file():
            raise FileNotFoundError(f"Downloaded file is unavailable: {source}")

        server_path = await asyncio.to_thread(self._server_file_path, source)
        result: Dict[str, Any] = {
            "enabled": True,
            "stored": True,
            "published": False,
            "server_path": server_path,
            "wms_url": self.wms_url,
        }
        if source.suffix.lower() not in {".tif", ".tiff"}:
            return result

        relative_identity = server_path
        digest = hashlib.sha1(relative_identity.encode("utf-8")).hexdigest()[:8]
        store_name = f"gh_{self._safe_name(source.stem)}_{digest}"
        workspace = quote(settings.geoserver_workspace, safe="")
        endpoint = (
            f"{self.rest_url}/rest/workspaces/{workspace}/coveragestores/"
            f"{quote(store_name, safe='')}/external.geotiff"
            "?configure=all&recalculate=nativebbox,latlonbbox"
        )

        async with self._client() as client:
            await self._ensure_workspace(client)
            response = await client.put(
                endpoint,
                content=server_path.encode("utf-8"),
                headers={"Content-Type": "text/plain"},
            )
            if response.status_code not in (200, 201):
                raise RuntimeError(
                    f"GeoServer could not publish {source.name} "
                    f"(HTTP {response.status_code}): {response.text[:500]}"
                )
            actual_layer_name = await self._resolve_store_layer_name(
                client, workspace, store_name, Path(server_path).stem
            )

        qualified_name = f"{settings.geoserver_workspace}:{actual_layer_name}"
        result.update({
            "published": True,
            "store": store_name,
            "layer": qualified_name,
            "layer_name": actual_layer_name,
            "wms_url": self.wms_url,
        })
        return result

    @staticmethod
    def _parse_color_ramp(expression: str) -> list[tuple[float, str, float]]:
        value = expression.strip()
        if value.startswith("[") and value.endswith("]"):
            value = value[1:-1]
        pieces = value.split(":")
        if len(pieces) < 4 or len(pieces) % 2:
            raise ValueError("A color ramp must contain value:color pairs")

        stops: list[tuple[float, str, float]] = []
        previous = -math.inf
        for index in range(0, len(pieces), 2):
            try:
                quantity = float(pieces[index])
            except ValueError as exc:
                raise ValueError("Color ramp values must be numeric") from exc
            color = pieces[index + 1].strip().lstrip("#").upper()
            if not math.isfinite(quantity) or quantity <= previous:
                raise ValueError("Color ramp values must be finite and strictly increasing")
            if not re.fullmatch(r"(?:[0-9A-F]{6}|[0-9A-F]{8})", color):
                raise ValueError("Colors must be 6 or 8 hexadecimal digits (RRGGBB[AA])")
            rgb = color[:6]
            opacity = int(color[6:8], 16) / 255 if len(color) == 8 else 1.0
            stops.append((quantity, f"#{rgb}", opacity))
            previous = quantity
        return stops

    @staticmethod
    def _ramp_sld(stops: list[tuple[float, str, float]]) -> str:
        entries = "".join(
            f'<ColorMapEntry color="{color}" quantity="{quantity:g}" opacity="{opacity:.6g}" />'
            for quantity, color, opacity in stops
        )
        return (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<StyledLayerDescriptor version="1.0.0" '
            'xmlns="http://www.opengis.net/sld" '
            'xmlns:ogc="http://www.opengis.net/ogc" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xsi:schemaLocation="http://www.opengis.net/sld '
            'http://schemas.opengis.net/sld/1.0.0/StyledLayerDescriptor.xsd">'
            '<NamedLayer><Name>GeoHarvest raster ramp</Name><UserStyle>'
            '<Title>GeoHarvest raster color ramp</Title><FeatureTypeStyle><Rule>'
            f'<RasterSymbolizer><ColorMap type="ramp">{entries}</ColorMap></RasterSymbolizer>'
            '</Rule></FeatureTypeStyle></UserStyle></NamedLayer></StyledLayerDescriptor>'
        )

    async def ensure_color_ramp(self, expression: str) -> str:
        stops = self._parse_color_ramp(expression)
        canonical = ":".join(f"{q:g}:{c}:{o:.6g}" for q, c, o in stops)
        style_name = f"gh_ramp_{hashlib.sha1(canonical.encode('ascii')).hexdigest()[:12]}"
        async with self._style_lock:
            async with self._client() as client:
                style_url = f"{self.rest_url}/rest/styles/{style_name}.json"
                existing = await client.get(style_url)
                if existing.status_code == 200:
                    return style_name
                if existing.status_code != 404:
                    existing.raise_for_status()
                response = await client.post(
                    f"{self.rest_url}/rest/styles?name={quote(style_name, safe='')}",
                    content=self._ramp_sld(stops).encode("utf-8"),
                    headers={"Content-Type": "application/vnd.ogc.sld+xml"},
                )
                if response.status_code == 409:
                    return style_name
                if response.status_code != 201:
                    raise RuntimeError(
                        f"GeoServer could not create the raster style "
                        f"(HTTP {response.status_code}): {response.text[:500]}"
                    )
        return style_name

    async def status(self) -> Dict[str, Any]:
        if not settings.geoserver_enabled:
            return {
                "enabled": False,
                "available": False,
                "wms_url": self.wms_url,
                "version": "1.3.0",
            }
        async with self._client() as client:
            response = await client.get(
                self.internal_wms_url,
                params={"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetCapabilities"},
            )
            available = response.status_code == 200 and b"WMS_Capabilities" in response.content
            return {
                "enabled": True,
                "available": available,
                "wms_url": self.wms_url,
                "version": "1.3.0",
                "status_code": response.status_code,
            }

    async def layers(self) -> Dict[str, Any]:
        if not settings.geoserver_enabled:
            return {"enabled": False, "workspace": settings.geoserver_workspace, "layers": []}
        async with self._client() as client:
            await self._ensure_workspace(client)
            response = await client.get(
                f"{self.rest_url}/rest/workspaces/"
                f"{quote(settings.geoserver_workspace, safe='')}/layers.json"
            )
            response.raise_for_status()
            payload = response.json()
        raw_layers = (payload.get("layers") or {}).get("layer") or []
        return {
            "enabled": True,
            "workspace": settings.geoserver_workspace,
            "layers": [
                {"name": item.get("name"), "href": item.get("href")}
                for item in raw_layers
                if isinstance(item, dict)
            ],
        }


geoserver_manager = GeoServerManager()


async def sync_known_downloads() -> None:
    """Publish existing completed downloads after GeoServer starts in Docker Compose."""
    if not settings.geoserver_enabled:
        return

    from backend.app.dependencies.database import SessionLocal
    from backend.app.models.models import Download, DownloadStatus

    for attempt in range(30):
        try:
            health = await geoserver_manager.status()
            if health.get("available"):
                break
        except Exception as exc:
            logger.debug("Waiting for GeoServer startup (%s/30): %s", attempt + 1, exc)
        if attempt < 29:
            await asyncio.sleep(2)
    else:
        logger.warning("GeoServer did not become available; existing downloads were not published")
        return

    db = SessionLocal()
    try:
        paths = {
            Path(item.destination).expanduser().resolve()
            for item in db.query(Download.destination)
            .filter(Download.status == DownloadStatus.COMPLETED)
            .all()
            if item.destination and ".staging" not in Path(item.destination).parts
        }
    finally:
        db.close()

    # Also recover raster files already present in the shared downloads folder that
    # predate download tracking or were written by a direct export endpoint.
    if settings.downloads_dir.exists():
        paths.update(
            path.resolve()
            for path in settings.downloads_dir.rglob("*")
            if path.is_file()
            and ".staging" not in path.parts
            and path.suffix.lower() in {".tif", ".tiff"}
        )

    semaphore = asyncio.Semaphore(3)

    async def sync_one(path: Path) -> None:
        if not path.is_file():
            return
        async with semaphore:
            try:
                result = await geoserver_manager.ingest(path)
                if result.get("published"):
                    logger.info("Published existing download to GeoServer: %s", result.get("layer"))
            except Exception as exc:
                logger.warning("Could not sync existing download %s to GeoServer: %s", path, exc)

    await asyncio.gather(*(sync_one(path) for path in sorted(paths)))
