"""Helpers for invoking synchronous PyLD code from async ACA-Py code.

PyLD's document-loader API is synchronous, but the loader needs async ACA-Py
services (DID resolution, caching).  Running PyLD in the default thread
executor lets the loader dispatch async work back to the main event loop via
``asyncio.run_coroutine_threadsafe``, avoiding both ``nest_asyncio`` and
nested event loops.
"""

import asyncio
import functools
from typing import Any, Callable


async def run_sync(func: Callable[..., Any], *args, **kwargs) -> Any:
    """Run *func* in the default thread executor and await its return value.

    This is intended for PyLD entry points such as ``jsonld.expand``,
    ``jsonld.compact``, ``jsonld.normalize`` and ``jsonld.frame``.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, functools.partial(func, *args, **kwargs))
