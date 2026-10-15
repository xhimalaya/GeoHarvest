import os
import time
import shutil
from pathlib import Path
from backend.core.sources.base import Connector, ConnectionTestResult


class LocalFileConnector(Connector):
    """Local Filesystem Connector with permission and disk availability verification."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    async def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        try:
            exists = self.root_dir.exists()
            if not exists:
                self.root_dir.mkdir(parents=True, exist_ok=True)

            # Test write access
            test_file = self.root_dir / ".geoharvest_test_probe"
            test_file.write_text("ok")
            test_file.unlink()

            usage = shutil.disk_usage(str(self.root_dir))
            latency = round((time.perf_counter() - start) * 1000.0, 1)

            return ConnectionTestResult(
                success=True,
                latency_ms=latency,
                message=f"Local path accessible ({latency}ms)",
                details={
                    "path": str(self.root_dir.resolve()),
                    "free_bytes": usage.free,
                    "total_bytes": usage.total
                }
            )
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000.0, 1)
            return ConnectionTestResult(
                success=False,
                latency_ms=latency,
                message=f"Filesystem error: {str(e)}",
                details={"error": str(e), "path": str(self.root_dir)}
            )
