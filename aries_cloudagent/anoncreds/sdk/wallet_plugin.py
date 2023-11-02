"""Utility for loading Postgres wallet plug-in."""

import logging
import platform
import json
from ctypes import cdll, c_char_p

EXTENSION = {"darwin": ".dylib", "linux": ".so", "win32": ".dll", "windows": ".dll"}
LOADED = False
LOGGER = logging.getLogger(__name__)


def file_ext():
    """Determine file extension based on platform."""
    your_platform = platform.system().lower()
    return EXTENSION[your_platform] if (your_platform in EXTENSION) else ".so"


def load_postgres_plugin(storage_config, storage_creds, raise_exc=False):
    """Load postgres dll and configure postgres wallet."""
    global LOADED, LOGGER

    if not LOADED:
        LOGGER.info(
            "Checking input postgres storage_config and storage_creds arguments"
        )
        try:
            json.loads(storage_config)
            json.loads(storage_creds)
        except json.decoder.JSONDecodeError:
            LOGGER.error(
                "Invalid stringified JSON input, check storage_config and storage_creds"
            )
            if raise_exc:
                raise OSError(
                    "Invalid stringified JSON input, "
                    "check storage_config and storage_creds"
                )
            else:
                raise SystemExit(1)

        LOGGER.info("Initializing postgres wallet")
        stg_lib = cdll.LoadLibrary("libindystrgpostgres" + file_ext())
        result = stg_lib.postgresstorage_init()
        if result != 0:
            LOGGER.error("Error unable to load postgres wallet storage: %s", result)
            if raise_exc:
                raise OSError(f"Error unable to load postgres wallet storage: {result}")
            else:
                raise SystemExit(1)
        if "wallet_scheme" in storage_config:
            c_config = c_char_p(storage_config.encode("utf-8"))
            c_credentials = c_char_p(storage_creds.encode("utf-8"))
            result = stg_lib.init_storagetype(c_config, c_credentials)
            if result != 0:
                LOGGER.error("Error unable to configure postgres stg: %s", result)
                if raise_exc:
                    raise OSError(f"Error unable to configure postgres stg: {result}")
                else:
                    raise SystemExit(1)
        LOADED = True

        LOGGER.info("Success, loaded postgres wallet storage")
