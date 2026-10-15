import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import Callable, Optional, Dict, Any
import httpx
from backend.app.models.models import DownloadStatus


class DownloadCancelledException(Exception):
    pass


class NonRetriableDownloadException(Exception):
    pass


class DownloadEngine:
    RETRIABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
    NON_RETRIABLE_STATUS_CODES = {400, 401, 403, 404}

    def __init__(
        self,
        chunk_size: int = 1024 * 1024,  # 1 MB
        max_attempts: int = 5,
        base_backoff_sec: float = 2.0
    ):
        self.chunk_size = chunk_size
        self.max_attempts = max_attempts
        self.base_backoff_sec = base_backoff_sec

    async def download_file(
        self,
        url: str,
        destination_path: Path,
        expected_size: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float, DownloadStatus, Optional[str]], None]] = None,
        cancellation_event: Optional[asyncio.Event] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Downloads a file with HTTP Range or S3 streaming support, writing to .part file first,
        and atomically renaming upon verification.
        """
        if url.startswith("s3://"):
            return await self._download_s3_file(
                url=url,
                destination_path=destination_path,
                expected_size=expected_size,
                expected_checksum=expected_checksum,
                progress_callback=progress_callback,
                cancellation_event=cancellation_event
            )

        part_path = Path(str(destination_path) + ".part")
        part_path.parent.mkdir(parents=True, exist_ok=True)

        # Check existing partial bytes
        downloaded_bytes = 0
        if part_path.exists():
            downloaded_bytes = part_path.stat().st_size

        attempt = 0
        base_headers = {
            "User-Agent": "GeoHarvest/0.1.0"
        }
        if headers:
            base_headers.update(headers)

        # Attach CDSE OData Bearer token if applicable
        from backend.app.dependencies.config import settings
        if "dataspace.copernicus.eu" in url and getattr(settings, "cdse_access_token", None) and "Authorization" not in base_headers:
            base_headers["Authorization"] = f"Bearer {settings.cdse_access_token}"

        while attempt < self.max_attempts:
            attempt += 1
            if cancellation_event and cancellation_event.is_set():
                if progress_callback:
                    progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.CANCELLED, "Cancelled by user")
                raise DownloadCancelledException("Download was cancelled")

            try:
                # Prepare Range header if partial bytes exist
                req_headers = dict(base_headers)
                if downloaded_bytes > 0:
                    req_headers["Range"] = f"bytes={downloaded_bytes}-"

                if progress_callback:
                    progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.DOWNLOADING, None)

                # Connect with streaming
                async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                    async with client.stream("GET", url, headers=req_headers) as response:
                        status_code = response.status_code

                        # Handle non-retriable HTTP errors
                        if status_code in self.NON_RETRIABLE_STATUS_CODES:
                            err_msg = f"Non-retriable HTTP error: {status_code}"
                            if progress_callback:
                                progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.FAILED, err_msg)
                            raise NonRetriableDownloadException(err_msg)

                        # Handle retriable HTTP errors
                        if status_code in self.RETRIABLE_STATUS_CODES:
                            retry_after = response.headers.get("Retry-After")
                            delay = float(retry_after) if retry_after and retry_after.isdigit() else (self.base_backoff_sec * (2 ** (attempt - 1)))
                            if progress_callback:
                                progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.RETRYING, f"HTTP {status_code}, retrying in {delay:.1f}s")
                            await asyncio.sleep(delay)
                            continue

                        # Check Range support
                        if status_code == 206:  # Partial Content
                            # Range request accepted; append to existing .part file
                            file_mode = "ab"
                            # Total size is downloaded + remaining
                            content_range = response.headers.get("Content-Range")
                            if content_range and "/" in content_range:
                                try:
                                    total_bytes = int(content_range.split("/")[-1])
                                except ValueError:
                                    total_bytes = expected_size or 0
                            else:
                                total_bytes = downloaded_bytes + int(response.headers.get("Content-Length", 0))
                        elif status_code == 200:  # Full Content
                            # Server does not support Range or fresh start; overwrite .part
                            file_mode = "wb"
                            downloaded_bytes = 0
                            total_bytes = int(response.headers.get("Content-Length", 0)) or (expected_size or 0)
                        elif status_code == 416:  # Range Not Satisfiable (file may already be complete)
                            if expected_size and downloaded_bytes == expected_size:
                                total_bytes = downloaded_bytes
                                file_mode = "ab"
                            else:
                                # Start over
                                downloaded_bytes = 0
                                file_mode = "wb"
                                continue
                        else:
                            response.raise_for_status()
                            total_bytes = expected_size or 0
                            file_mode = "wb"

                        start_time = time.time()
                        last_report_time = start_time
                        last_report_bytes = downloaded_bytes

                        # Open and stream chunks
                        with open(part_path, file_mode) as f:
                            async for chunk in response.aiter_bytes(chunk_size=self.chunk_size):
                                if cancellation_event and cancellation_event.is_set():
                                    if progress_callback:
                                        progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.CANCELLED, "Cancelled by user")
                                    raise DownloadCancelledException("Download cancelled")

                                f.write(chunk)
                                downloaded_bytes += len(chunk)

                                now = time.time()
                                if now - last_report_time >= 0.5:
                                    time_delta = now - last_report_time
                                    bytes_delta = downloaded_bytes - last_report_bytes
                                    speed = bytes_delta / time_delta if time_delta > 0 else 0.0
                                    last_report_time = now
                                    last_report_bytes = downloaded_bytes
                                    if progress_callback:
                                        progress_callback(downloaded_bytes, total_bytes, speed, DownloadStatus.DOWNLOADING, None)

                        # Download finished for this asset
                        if progress_callback:
                            progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.VERIFYING, "Verifying checksum and file size...")

                        # Size verification
                        actual_size = part_path.stat().st_size
                        if total_bytes > 0 and actual_size != total_bytes:
                            raise ValueError(f"Size mismatch: expected {total_bytes} bytes, got {actual_size} bytes")

                        # Checksum verification if available
                        if expected_checksum:
                            hasher = hashlib.sha256()
                            with open(part_path, "rb") as vf:
                                while b := vf.read(1024 * 1024):
                                    hasher.update(b)
                            computed_hash = hasher.hexdigest()
                            if computed_hash.lower() != expected_checksum.lower():
                                raise ValueError(f"Checksum mismatch: expected {expected_checksum}, calculated {computed_hash}")

                        # Atomic rename from .part to final destination
                        if destination_path.exists():
                            destination_path.unlink()
                        part_path.rename(destination_path)

                        if progress_callback:
                            progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.COMPLETED, None)

                        return True

            except DownloadCancelledException:
                raise
            except NonRetriableDownloadException as e:
                err_msg = str(e)
                if progress_callback:
                    progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.FAILED, f"Download failed: {err_msg}")
                return False
            except Exception as e:
                err_msg = str(e)
                if attempt < self.max_attempts:
                    delay = self.base_backoff_sec * (2 ** (attempt - 1))
                    if progress_callback:
                        progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.RETRYING, f"Error: {err_msg}. Retrying in {delay:.1f}s (Attempt {attempt}/{self.max_attempts})")
                    await asyncio.sleep(delay)
                else:
                    if progress_callback:
                        progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.FAILED, f"Failed after {self.max_attempts} attempts: {err_msg}")
                    return False

        return False

    async def _download_s3_file(
        self,
        url: str,
        destination_path: Path,
        expected_size: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float, DownloadStatus, Optional[str]], None]] = None,
        cancellation_event: Optional[asyncio.Event] = None
    ) -> bool:
        """
        Downloads an object from S3 (e.g. s3://eodata/...) with chunk streaming, Range resumption,
        progress reporting, and atomic rename. Falls back to public AWS mirror for Sentinel-2 if S3 keys missing.
        """
        import re
        from backend.app.dependencies.config import settings

        part_path = Path(str(destination_path) + ".part")
        part_path.parent.mkdir(parents=True, exist_ok=True)

        parts = url[5:].split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""

        downloaded_bytes = 0
        if part_path.exists():
            downloaded_bytes = part_path.stat().st_size

        access_key = settings.cdse_s3_access_key or os.environ.get("GEOHARVEST_CDSE_S3_ACCESS_KEY")
        secret_key = settings.cdse_s3_secret_key or os.environ.get("GEOHARVEST_CDSE_S3_SECRET_KEY")
        endpoint = settings.cdse_s3_endpoint or os.environ.get("GEOHARVEST_CDSE_S3_ENDPOINT", "https://eodata.dataspace.copernicus.eu")

        # Fallback to open AWS Sentinel-2 COG if S3 keys are absent
        if not access_key or not secret_key:
            m = re.search(r"(S2[AB])_.*?_T(\d{2})([A-Z])([A-Z]{2})_(\d{4})(\d{2})(\d{2})", url)
            if m:
                sat, utm, band_code, sq, year, month, day = m.groups()
                month_int = str(int(month))
                aws_id = f"{sat}_{utm}{band_code}{sq}_{year}{month}{day}_0_L2A"
                bm = re.search(r"_([A-Z0-9]+)_(?:10m|20m|60m)\.jp2", url)
                band = bm.group(1).upper() if bm else "B02"
                fallback_url = f"https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/{utm}/{band_code}/{sq}/{year}/{month_int}/{aws_id}/{band}.tif"
                return await self.download_file(
                    url=fallback_url,
                    destination_path=destination_path,
                    expected_size=expected_size,
                    expected_checksum=expected_checksum,
                    progress_callback=progress_callback,
                    cancellation_event=cancellation_event
                )
            else:
                err_msg = "S3 credentials missing. Please configure CDSE S3 Access Key & Secret Key in Credentials settings."
                if progress_callback:
                    progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.FAILED, err_msg)
                return False

        import boto3
        s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="default"
        )

        attempt = 0
        while attempt < self.max_attempts:
            attempt += 1
            if cancellation_event and cancellation_event.is_set():
                if progress_callback:
                    progress_callback(downloaded_bytes, expected_size or 0, 0.0, DownloadStatus.CANCELLED, "Cancelled by user")
                raise DownloadCancelledException("Download was cancelled")

            try:
                total_bytes = expected_size or 0
                if total_bytes == 0:
                    head = await asyncio.to_thread(s3.head_object, Bucket=bucket, Key=key)
                    total_bytes = int(head.get("ContentLength", 0))

                get_kwargs: Dict[str, Any] = {"Bucket": bucket, "Key": key}
                file_mode = "wb"
                if downloaded_bytes > 0 and downloaded_bytes < total_bytes:
                    get_kwargs["Range"] = f"bytes={downloaded_bytes}-"
                    file_mode = "ab"
                else:
                    downloaded_bytes = 0
                    file_mode = "wb"

                if progress_callback:
                    progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.DOWNLOADING, None)

                resp = await asyncio.to_thread(s3.get_object, **get_kwargs)
                body = resp["Body"]

                start_time = time.time()
                last_report_time = start_time
                last_report_bytes = downloaded_bytes

                with open(part_path, file_mode) as f:
                    while True:
                        if cancellation_event and cancellation_event.is_set():
                            if progress_callback:
                                progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.CANCELLED, "Cancelled by user")
                            raise DownloadCancelledException("Download was cancelled")

                        chunk = await asyncio.to_thread(body.read, self.chunk_size)
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        now = time.time()
                        if now - last_report_time >= 0.5:
                            time_delta = now - last_report_time
                            bytes_delta = downloaded_bytes - last_report_bytes
                            speed = bytes_delta / time_delta if time_delta > 0 else 0.0
                            last_report_time = now
                            last_report_bytes = downloaded_bytes
                            if progress_callback:
                                progress_callback(downloaded_bytes, total_bytes, speed, DownloadStatus.DOWNLOADING, None)

                # Verification
                if progress_callback:
                    progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.VERIFYING, "Verifying downloaded file...")

                actual_size = part_path.stat().st_size
                if total_bytes > 0 and actual_size != total_bytes:
                    raise ValueError(f"Size mismatch: expected {total_bytes} bytes, got {actual_size} bytes")

                if expected_checksum:
                    hasher = hashlib.sha256()
                    with open(part_path, "rb") as vf:
                        while b := vf.read(1024 * 1024):
                            hasher.update(b)
                    computed_hash = hasher.hexdigest()
                    if computed_hash.lower() != expected_checksum.lower():
                        raise ValueError(f"Checksum mismatch: expected {expected_checksum}, calculated {computed_hash}")

                if destination_path.exists():
                    destination_path.unlink()
                part_path.rename(destination_path)

                if progress_callback:
                    progress_callback(downloaded_bytes, total_bytes, 0.0, DownloadStatus.COMPLETED, None)

                return True

            except DownloadCancelledException:
                raise
            except Exception as e:
                err_msg = str(e)
                if attempt < self.max_attempts:
                    delay = self.base_backoff_sec * (2 ** (attempt - 1))
                    if progress_callback:
                        progress_callback(
                            downloaded_bytes,
                            expected_size or 0,
                            0.0,
                            DownloadStatus.RETRYING,
                            f"S3 Error: {err_msg}. Retrying in {delay:.1f}s (Attempt {attempt}/{self.max_attempts})"
                        )
                    await asyncio.sleep(delay)
                else:
                    if progress_callback:
                        progress_callback(
                            downloaded_bytes,
                            expected_size or 0,
                            0.0,
                            DownloadStatus.FAILED,
                            f"S3 download failed after {self.max_attempts} attempts: {err_msg}"
                        )
                    return False

        return False
