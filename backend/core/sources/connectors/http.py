import time
import httpx
from typing import Dict, Any, Optional
from backend.core.sources.base import Connector, ConnectionTestResult


class HttpConnector(Connector):
    """HTTP/HTTPS Connector with connection testing and latency measurement."""

    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {"User-Agent": "GeoHarvest/0.2.0"}
        self.timeout = timeout

    async def test_connection(self) -> ConnectionTestResult:
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(self.base_url, headers=self.headers)
                latency = round((time.perf_counter() - start) * 1000.0, 1)
                success = resp.status_code in [200, 204]
                return ConnectionTestResult(
                    success=success,
                    latency_ms=latency,
                    message=f"HTTP {resp.status_code} ({latency}ms)" if success else f"HTTP error {resp.status_code}",
                    details={
                        "status_code": resp.status_code,
                        "url": self.base_url,
                        "server": resp.headers.get("server", "unknown")
                    }
                )
        except Exception as e:
            latency = round((time.perf_counter() - start) * 1000.0, 1)
            return ConnectionTestResult(
                success=False,
                latency_ms=latency,
                message=f"Connection failed: {str(e)}",
                details={"error": str(e), "url": self.base_url}
            )
