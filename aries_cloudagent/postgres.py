"""Utility for loading Postgres wallet plug-in."""

import sys
from ctypes import cdll
import platform


EXTENSION = {"darwin": ".dylib", "linux": ".so", "win32": ".dll", "windows": ".dll"}


def file_ext():
    """Determine file extension based on platform."""
    your_platform = platform.system().lower()
    return EXTENSION[your_platform] if (your_platform in EXTENSION) else ".so"


def load_postgres_plugin():
    """Load postgres dll and configure postgres wallet."""
    print("Initializing postgres wallet")
    stg_lib = cdll.LoadLibrary("libindystrgpostgres" + file_ext())
    result = stg_lib.postgresstorage_init()
    if result != 0:
        print("\nError unable to load postgres wallet storage", result)
        sys.exit(0)

    print("Success, loaded postgres wallet storage")
