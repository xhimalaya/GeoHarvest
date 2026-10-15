from pathlib import Path
from typing import Optional, Callable, Any, Dict
from backend.core.sources.base import TransferAdapter
from backend.core.download.engine import DownloadEngine
from backend.app.models.models import DownloadStatus


class HttpTransferAdapter(TransferAdapter):
    """HTTP/HTTPS Transfer Adapter leveraging the resilient DownloadEngine."""

    def __init__(self, download_engine: Optional[DownloadEngine] = None):
        self.download_engine = download_engine or DownloadEngine()

    async def transfer(
        self,
        url_or_path: str,
        destination_path: Any,
        expected_size: Optional[int] = None,
        expected_checksum: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, float, DownloadStatus, Optional[str]], None]] = None,
        cancellation_event: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> bool:
        dest = Path(destination_path)
        return await self.download_engine.download_file(
            url=url_or_path,
            destination_path=dest,
            expected_size=expected_size,
            expected_checksum=expected_checksum,
            progress_callback=progress_callback,
            cancellation_event=cancellation_event,
            headers=headers
        )
