import os
import asyncio
import functools
import logging
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from typing import Callable, Any, Optional
from backend.app.dependencies.config import settings

logger = logging.getLogger("geoharvest.processing.executor")


class GeoProcessExecutor:
    """
    Manages a dedicated ProcessPoolExecutor to offload CPU-bound Rasterio/GDAL
    geoprocessing tasks completely outside the asyncio event loop and free from the GIL.
    Uses 'spawn' multiprocessing context for GDAL/Rasterio safety across Unix platforms.
    """
    _executor: Optional[ProcessPoolExecutor] = None

    @classmethod
    def get_executor(cls) -> ProcessPoolExecutor:
        if cls._executor is None:
            max_workers = getattr(settings, "max_processing_workers", None) or min(os.cpu_count() or 4, 8)
            logger.info(f"Initializing GeoProcessExecutor with {max_workers} worker processes (spawn context)...")
            ctx = mp.get_context("spawn")
            cls._executor = ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)
        return cls._executor

    @classmethod
    async def run_cpu_bound(cls, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Executes a CPU-bound geoprocessing function in a separate process pool worker,
        returning an awaitable asyncio Future.
        """
        loop = asyncio.get_running_loop()
        executor = cls.get_executor()
        if kwargs:
            call = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(executor, call)
        return await loop.run_in_executor(executor, func, *args)

    @classmethod
    def shutdown(cls, wait: bool = True):
        """Gracefully shuts down the process pool executor."""
        if cls._executor is not None:
            logger.info("Shutting down GeoProcessExecutor process pool...")
            cls._executor.shutdown(wait=wait)
            cls._executor = None
