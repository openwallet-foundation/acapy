import os
import sys
from unittest import mock

import pytest

INDY_FOUND = False
INDY_STUB = None
POSTGRES_URL = None


def pytest_sessionstart(session):
    global INDY_FOUND, INDY_STUB, POSTGRES_URL

    # detect indy module
    try:
        from indy.libindy import _cdll

        _cdll()

        INDY_FOUND = True
    except ImportError:
        print("Skipping Indy-specific tests: python3-indy module not installed.")
    except OSError:
        print(
            "Skipping Indy-specific tests: libindy shared library could not be loaded."
        )

    if not INDY_FOUND:
        modules = {}
        package_name = "indy"
        modules[package_name] = mock.MagicMock()
        for mod in [
            "anoncreds",
            "crypto",
            "did",
            "error",
            "pool",
            "ledger",
            "non_secrets",
            "pairwise",
            "wallet",
        ]:
            submod = f"{package_name}.{mod}"
            modules[submod] = mock.MagicMock()
        INDY_STUB = mock.patch.dict(sys.modules, modules)
        INDY_STUB.start()

    POSTGRES_URL = os.getenv("POSTGRES_URL")


def pytest_sessionfinish(session):
    global INDY_STUB
    if INDY_STUB:
        INDY_STUB.stop()
        INDY_STUB = None


def pytest_runtest_setup(item: pytest.Item):

    if tuple(item.iter_markers(name="indy")) and not INDY_FOUND:
        pytest.skip("test requires Indy support")

    if tuple(item.iter_markers(name="postgres")) and not POSTGRES_URL:
        pytest.skip("test requires Postgres support")
