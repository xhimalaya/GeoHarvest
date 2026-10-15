import os
import shutil
import mimetypes
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
import psutil

from backend.app.dependencies.config import settings
from backend.app.schemas.schemas import (
    StorageEstimateRequest,
    StorageEstimateResponse,
    StorageItem,
    BreadcrumbItem,
    FileExplorerResponse,
    StorageDestinationInfo,
    SetDestinationRequest,
    DirectoryPickerItem,
    DirectoryShortcut,
    DirectoryBrowseResponse,
    CreateDirectoryRequest,
)
from backend.core.storage.estimator import storage_estimator

router = APIRouter(prefix="/api/storage", tags=["storage"])

# Active custom destination directory in memory (defaults to settings.downloads_dir)
_custom_destination_dir: Optional[Path] = None


def get_active_download_dir() -> Path:
    global _custom_destination_dir
    if _custom_destination_dir and _custom_destination_dir.exists():
        return _custom_destination_dir
    return settings.downloads_dir.resolve()


def get_allowed_roots() -> Dict[str, Path]:
    active = get_active_download_dir()
    roots = {
        "downloads": active,
        "default_downloads": settings.downloads_dir.resolve(),
        "processed": (settings.data_dir / "processed").resolve(),
        "aois": settings.aois_dir.resolve(),
        "data": settings.data_dir.resolve(),
    }
    return roots


def format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024.0
    return f"{size:.1f} PB"


def resolve_safe_path(rel_path: str, root_name: str = "downloads") -> Path:
    roots = get_allowed_roots()
    base_root = roots.get(root_name, roots["downloads"])
    cleaned = (rel_path or "").strip().lstrip("/\\")

    resolved = (base_root / cleaned).resolve()
    # Path traversal safety check
    is_safe = False
    for r in roots.values():
        try:
            if resolved == r or resolved.is_relative_to(r):
                is_safe = True
                break
        except AttributeError:
            # Python < 3.9 fallback
            if str(resolved).startswith(str(r)):
                is_safe = True
                break

    if not is_safe:
        raise HTTPException(status_code=403, detail="Access denied: path traverses outside allowed storage directories")
    return resolved


@router.post("/estimate", response_model=StorageEstimateResponse)
async def estimate_storage(request: StorageEstimateRequest):
    return storage_estimator.estimate(
        scenes=request.selected_scenes,
        selected_bands=request.selected_bands
    )


@router.get("/destination", response_model=StorageDestinationInfo)
async def get_storage_destination():
    active_dir = get_active_download_dir()
    default_dir = settings.downloads_dir.resolve()
    active_dir.mkdir(parents=True, exist_ok=True)

    try:
        disk = psutil.disk_usage(str(active_dir))
        total = disk.total
        used = disk.used
        free = disk.free
        pct = disk.percent
    except Exception:
        total = 0
        used = 0
        free = 0
        pct = 0.0

    is_writable = os.access(str(active_dir), os.W_OK)

    return StorageDestinationInfo(
        default_directory=str(default_dir),
        active_directory=str(active_dir),
        is_custom=bool(_custom_destination_dir and _custom_destination_dir != default_dir),
        exists=active_dir.exists(),
        is_writable=is_writable,
        disk_total_bytes=total,
        disk_used_bytes=used,
        disk_free_bytes=free,
        disk_percent=pct,
    )


@router.post("/destination", response_model=StorageDestinationInfo)
async def set_storage_destination(req: SetDestinationRequest):
    global _custom_destination_dir
    raw_path = (req.directory or "").strip()
    if not raw_path:
        _custom_destination_dir = None
        return await get_storage_destination()

    target_path = Path(raw_path).expanduser().resolve()
    try:
        target_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot create directory '{target_path}': {str(e)}")

    if not os.access(str(target_path), os.W_OK):
        raise HTTPException(status_code=400, detail=f"Directory '{target_path}' is not writable")

    _custom_destination_dir = target_path
    return await get_storage_destination()


@router.get("/files", response_model=FileExplorerResponse)
async def list_files(
    path: str = Query("", description="Relative path within root directory"),
    root: str = Query("downloads", description="Storage root: downloads, processed, aois, or data")
):
    roots = get_allowed_roots()
    base_root = roots.get(root, roots["downloads"])
    base_root.mkdir(parents=True, exist_ok=True)

    target_dir = resolve_safe_path(path, root)
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    if not target_dir.is_dir():
        raise HTTPException(status_code=400, detail="Target path is a file, not a directory")

    # Construct relative path from base root
    try:
        rel_to_base = target_dir.relative_to(base_root)
        current_rel = "" if str(rel_to_base) == "." else str(rel_to_base).replace("\\", "/")
    except ValueError:
        current_rel = ""

    # Build breadcrumbs
    breadcrumbs = [BreadcrumbItem(name="Downloads" if root == "downloads" else root.capitalize(), path="")]
    if current_rel:
        accum = []
        for part in current_rel.split("/"):
            if part:
                accum.append(part)
                breadcrumbs.append(BreadcrumbItem(name=part, path="/".join(accum)))

    parent_path = None
    if current_rel:
        parent_parts = current_rel.split("/")[:-1]
        parent_path = "/".join(parent_parts)

    folders: List[StorageItem] = []
    files: List[StorageItem] = []
    total_size = 0

    try:
        for entry in target_dir.iterdir():
            # Skip hidden and temporary files
            if entry.name.startswith(".") and not entry.name.startswith(".part"):
                continue

            entry_rel = f"{current_rel}/{entry.name}".lstrip("/")
            st = entry.stat()
            mod_time = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat()

            if entry.is_dir():
                try:
                    children = [c for c in entry.iterdir() if not c.name.startswith(".")]
                    item_count = len(children)
                    # Calculate directory size
                    dir_size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
                except Exception:
                    item_count = 0
                    dir_size = 0

                folders.append(
                    StorageItem(
                        name=entry.name,
                        relative_path=entry_rel,
                        absolute_path=str(entry),
                        is_dir=True,
                        size_bytes=dir_size,
                        formatted_size=format_bytes(dir_size),
                        modified_at=mod_time,
                        item_count=item_count,
                    )
                )
            elif entry.is_file():
                f_size = st.st_size
                total_size += f_size
                ext = entry.suffix.lower()
                mime, _ = mimetypes.guess_type(entry.name)

                is_img = ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"]
                is_rst = ext in [".tif", ".tiff", ".jp2"]
                is_geo = ext in [".geojson"] or (ext == ".json" and "geojson" in entry.name.lower())
                is_meta = ext in [".json", ".xml", ".txt", ".md", ".yaml", ".yml"]

                files.append(
                    StorageItem(
                        name=entry.name,
                        relative_path=entry_rel,
                        absolute_path=str(entry),
                        is_dir=False,
                        size_bytes=f_size,
                        formatted_size=format_bytes(f_size),
                        modified_at=mod_time,
                        extension=ext,
                        mime_type=mime or "application/octet-stream",
                        is_image=is_img,
                        is_raster=is_rst,
                        is_geojson=is_geo,
                        is_metadata=is_meta,
                    )
                )
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied reading directory")

    # Sort folders alphabetically, files by modified time descending
    folders.sort(key=lambda x: x.name.lower())
    files.sort(key=lambda x: x.name.lower())

    return FileExplorerResponse(
        current_path=current_rel,
        parent_path=parent_path,
        absolute_path=str(target_dir),
        breadcrumbs=breadcrumbs,
        folders=folders,
        files=files,
        total_folders=len(folders),
        total_files=len(files),
        total_size_bytes=total_size,
        formatted_total_size=format_bytes(total_size),
    )


@router.get("/download")
async def download_file(
    path: str = Query(..., description="Relative path of file to download"),
    root: str = Query("downloads", description="Storage root")
):
    target_path = resolve_safe_path(path, root)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if not target_path.is_file():
        raise HTTPException(status_code=400, detail="Requested path is a directory, not a file")

    mime, _ = mimetypes.guess_type(target_path.name)
    return FileResponse(
        path=target_path,
        media_type=mime or "application/octet-stream",
        filename=target_path.name,
    )


@router.get("/preview")
async def preview_file(
    path: str = Query(..., description="Relative path of file to preview"),
    root: str = Query("downloads", description="Storage root")
):
    target_path = resolve_safe_path(path, root)
    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    mime, _ = mimetypes.guess_type(target_path.name)
    ext = target_path.suffix.lower()

    if ext in [".jpg", ".jpeg", ".png", ".webp", ".bmp"]:
        return FileResponse(path=target_path, media_type=mime or "image/jpeg")
    elif ext in [".json", ".geojson"]:
        return FileResponse(path=target_path, media_type="application/json")
    elif ext in [".txt", ".xml", ".md"]:
        return FileResponse(path=target_path, media_type="text/plain")
    else:
        # Return as binary stream
        return FileResponse(path=target_path, media_type=mime or "application/octet-stream")


@router.delete("/file")
async def delete_storage_item(
    path: str = Query(..., description="Relative path of file or folder to delete"),
    root: str = Query("downloads", description="Storage root")
):
    clean_rel = (path or "").strip().lstrip("/\\")
    if not clean_rel:
        raise HTTPException(status_code=400, detail="Cannot delete root storage directory")

    target_path = resolve_safe_path(clean_rel, root)
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        if target_path.is_dir():
            shutil.rmtree(target_path)
            return {"deleted": True, "type": "directory", "path": clean_rel}
        else:
            target_path.unlink()
            return {"deleted": True, "type": "file", "path": clean_rel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete item: {str(e)}")


@router.get("/search", response_model=List[StorageItem])
async def search_storage(
    query: str = Query(..., min_length=1, description="Search query string"),
    root: str = Query("downloads", description="Storage root")
):
    roots = get_allowed_roots()
    base_root = roots.get(root, roots["downloads"])
    if not base_root.exists():
        return []

    q_lower = query.lower().strip()
    matches: List[StorageItem] = []

    try:
        for entry in base_root.rglob("*"):
            if len(matches) >= 60:
                break
            if entry.name.startswith(".") and not entry.name.startswith(".part"):
                continue

            if q_lower in entry.name.lower():
                try:
                    rel = str(entry.relative_to(base_root)).replace("\\", "/")
                    st = entry.stat()
                    mod_time = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat()
                    is_dir = entry.is_dir()

                    ext = entry.suffix.lower() if not is_dir else None
                    mime, _ = mimetypes.guess_type(entry.name) if not is_dir else (None, None)

                    matches.append(
                        StorageItem(
                            name=entry.name,
                            relative_path=rel,
                            absolute_path=str(entry),
                            is_dir=is_dir,
                            size_bytes=st.st_size if not is_dir else 0,
                            formatted_size=format_bytes(st.st_size if not is_dir else 0),
                            modified_at=mod_time,
                            extension=ext,
                            mime_type=mime,
                            is_image=ext in [".jpg", ".jpeg", ".png", ".webp"] if ext else False,
                            is_raster=ext in [".tif", ".tiff", ".jp2"] if ext else False,
                            is_geojson=ext in [".geojson"] or (ext == ".json" and "geojson" in entry.name.lower()) if ext else False,
                            is_metadata=ext in [".json", ".xml", ".txt"] if ext else False,
                        )
                    )
                except Exception:
                    continue
    except Exception:
        pass

    return matches


@router.get("/directories", response_model=DirectoryBrowseResponse)
async def browse_directories(
    path: Optional[str] = Query(None, description="Absolute or relative path to browse")
):
    if not path or not path.strip():
        target_path = get_active_download_dir()
    else:
        target_path = Path(path.strip()).expanduser().resolve()

    if not target_path.exists():
        target_path = Path.home()
        if not target_path.exists():
            target_path = settings.downloads_dir.resolve()
            target_path.mkdir(parents=True, exist_ok=True)

    if not target_path.is_dir():
        target_path = target_path.parent

    # Build breadcrumbs
    parts = target_path.parts
    breadcrumbs: List[BreadcrumbItem] = []
    if parts:
        accum = Path(parts[0])
        breadcrumbs.append(BreadcrumbItem(name=parts[0], path=str(accum)))
        for p in parts[1:]:
            accum = accum / p
            breadcrumbs.append(BreadcrumbItem(name=p, path=str(accum)))

    parent_path = str(target_path.parent) if target_path.parent != target_path else None

    # Shortcuts
    home_dir = Path.home()
    default_dl = settings.downloads_dir.resolve()
    default_dl.mkdir(parents=True, exist_ok=True)

    shortcuts: List[DirectoryShortcut] = [
        DirectoryShortcut(name="GeoHarvest Default", path=str(default_dl), icon="download"),
        DirectoryShortcut(name="Home", path=str(home_dir), icon="home"),
    ]

    downloads_folder = home_dir / "Downloads"
    if downloads_folder.exists() and downloads_folder.is_dir():
        shortcuts.append(DirectoryShortcut(name="Downloads", path=str(downloads_folder), icon="folder-download"))

    desktop_folder = home_dir / "Desktop"
    if desktop_folder.exists() and desktop_folder.is_dir():
        shortcuts.append(DirectoryShortcut(name="Desktop", path=str(desktop_folder), icon="desktop"))

    docs_folder = home_dir / "Documents"
    if docs_folder.exists() and docs_folder.is_dir():
        shortcuts.append(DirectoryShortcut(name="Documents", path=str(docs_folder), icon="file-text"))

    # Telemetry
    try:
        disk = psutil.disk_usage(str(target_path))
        free_bytes = disk.free
    except Exception:
        free_bytes = 0

    is_writable = os.access(str(target_path), os.W_OK)

    # Subdirectories
    subdirs: List[DirectoryPickerItem] = []
    try:
        for entry in target_path.iterdir():
            if entry.is_dir() and not entry.name.startswith("."):
                try:
                    st = entry.stat()
                    mod_time = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat()
                    w = os.access(str(entry), os.W_OK)
                except Exception:
                    mod_time = ""
                    w = False
                subdirs.append(
                    DirectoryPickerItem(
                        name=entry.name,
                        path=str(entry),
                        is_writable=w,
                        modified_at=mod_time,
                    )
                )
    except PermissionError:
        pass
    except Exception:
        pass

    subdirs.sort(key=lambda x: x.name.lower())

    return DirectoryBrowseResponse(
        current_path=str(target_path),
        parent_path=parent_path,
        breadcrumbs=breadcrumbs,
        directories=subdirs,
        is_writable=is_writable,
        free_bytes=free_bytes,
        formatted_free=format_bytes(free_bytes),
        shortcuts=shortcuts,
    )


@router.post("/create-directory", response_model=DirectoryPickerItem)
async def create_storage_directory(req: CreateDirectoryRequest):
    clean_parent = (req.parent_path or "").strip()
    if not clean_parent:
        raise HTTPException(status_code=400, detail="Parent path is required")

    parent = Path(clean_parent).expanduser().resolve()
    if not parent.exists() or not parent.is_dir():
        raise HTTPException(status_code=400, detail="Parent directory does not exist")

    if not os.access(str(parent), os.W_OK):
        raise HTTPException(status_code=403, detail="Parent directory is not writable")

    clean_name = req.name.strip()
    if not clean_name or "/" in clean_name or "\\" in clean_name or clean_name.startswith("."):
        raise HTTPException(status_code=400, detail="Invalid directory name")

    new_dir = parent / clean_name
    if new_dir.exists():
        raise HTTPException(status_code=400, detail="Directory already exists")

    try:
        new_dir.mkdir(parents=False, exist_ok=False)
        st = new_dir.stat()
        mod_time = datetime.datetime.fromtimestamp(st.st_mtime, datetime.timezone.utc).isoformat()
        return DirectoryPickerItem(
            name=new_dir.name,
            path=str(new_dir),
            is_writable=os.access(str(new_dir), os.W_OK),
            modified_at=mod_time,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create directory: {str(e)}")

