"""Helpers for invoking synchronous PyLD code from async ACA-Py code.

PyLD's document-loader API is synchronous, but the loader needs async ACA-Py
services (DID resolution, caching).  Running PyLD in a dedicated thread
executor lets the loader dispatch async work back to the main event loop via
``asyncio.run_coroutine_threadsafe``, avoiding both ``nest_asyncio`` and
nested event loops. A dedicated pool also keeps the asyncio default executor
free for other work such as aiohttp DNS resolution, preventing deadlock when
many PyLD calls are in flight.
"""

import asyncio
import atexit
import functools
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

# Dedicated executor for PyLD work. Keeping this separate from the asyncio
# default executor avoids starving the default pool, which aiohttp uses for
# blocking DNS lookups while PyLD worker threads are themselves blocked
# waiting on DID resolution from the event loop.
_PYLD_EXECUTOR = ThreadPoolExecutor(
    max_workers=min(32, (os.cpu_count() or 1) + 4),
    thread_name_prefix="pyld",
)
atexit.register(_PYLD_EXECUTOR.shutdown, wait=True)


async def run_sync(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Run *func* in the PyLD thread executor and await its return value.

    This is intended for PyLD entry points such as ``jsonld.expand``,
    ``jsonld.compact``, ``jsonld.normalize`` and ``jsonld.frame``.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _PYLD_EXECUTOR, functools.partial(func, *args, **kwargs)
    )
