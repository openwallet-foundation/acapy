"""Utility for loading Postgres wallet plug-in."""

import logging
import platform
from ctypes import cdll

EXTENSION = {"darwin": ".dylib", "linux": ".so", "win32": ".dll", "windows": ".dll"}
LOADED = False
LOGGER = logging.getLogger(__name__)


def file_ext():
    """Determine file extension based on platform."""
    your_platform = platform.system().lower()
    return EXTENSION[your_platform] if (your_platform in EXTENSION) else ".so"


def load_postgres_plugin(raise_exc=False):
    """Load postgres dll and configure postgres wallet."""
    global LOADED, LOGGER

    if not LOADED:
        LOGGER.info("Initializing postgres wallet")
        stg_lib = cdll.LoadLibrary("libindystrgpostgres" + file_ext())
        result = stg_lib.postgresstorage_init()
        if result != 0:
            LOGGER.error("Error unable to load postgres wallet storage: %s", result)
            if raise_exc:
                raise OSError(f"Error unable to load postgres wallet storage: {result}")
            else:
                raise SystemExit(1)
        LOADED = True

        LOGGER.info("Success, loaded postgres wallet storage")
