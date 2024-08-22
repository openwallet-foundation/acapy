import os
import sys
from unittest import mock

import pytest

STUBS = {}

POSTGRES_URL = None
ENABLE_PTVSD = None


class Stub:
    def __init__(self, inner):
        self.inner = inner

    @property
    def found(self) -> bool:
        return not self.inner

    def start(self):
        self.inner and self.inner.start()

    def stop(self):
        self.inner and self.inner.stop()


def stub_anoncreds() -> Stub:
    # detect anoncreds library
    try:
        from anoncreds import generate_nonce

        _ = generate_nonce()
        return Stub(None)
    except ImportError:
        print("Skipping Anoncreds-specific tests: anoncreds module not installed.")
    except OSError:
        print(
            "Skipping Anoncreds-specific tests: anoncreds shared library"
            "could not be loaded."
        )

    modules = {}
    package_name = "anoncreds"
    modules[package_name] = mock.MagicMock()
    return Stub(mock.patch.dict(sys.modules, modules))


def stub_askar() -> Stub:
    # detect aries-askar library
    try:
        from aries_askar.bindings import get_library

        get_library()
        return Stub(None)
    except ImportError:
        print("Skipping Askar-specific tests: aries_askar module not installed.")
    except OSError:
        print(
            "Skipping Askar-specific tests: aries-askar shared library"
            "could not be loaded."
        )

    modules = {}
    package_name = "aries_askar"
    modules[package_name] = mock.MagicMock()
    for mod in [
        "bindings",
        "error",
        "store",
        "types",
    ]:
        submod = f"{package_name}.{mod}"
        modules[submod] = mock.MagicMock()
    return Stub(mock.patch.dict(sys.modules, modules))


def stub_indy_credx() -> Stub:
    # detect indy-credx library
    try:
        from indy_credx.bindings import get_library

        get_library()
        return Stub(None)
    except ImportError:
        print("Skipping Indy-Credx-specific tests: indy_credx module not installed.")
    except OSError:
        print(
            "Skipping Indy-Credx-specific tests: indy-credx shared library"
            "could not be loaded."
        )

    modules = {}
    package_name = "indy_credx"
    modules[package_name] = mock.MagicMock()
    return Stub(mock.patch.dict(sys.modules, modules))


def stub_indy_vdr() -> Stub:
    # detect indy-vdr library
    try:
        from indy_vdr.bindings import get_library

        get_library()
        return Stub(None)
    except ImportError:
        print("Skipping Indy-VDR-specific tests: indy_vdr module not installed.")
    except OSError:
        print(
            "Skipping Indy-VDR-specific tests: indy-vdr shared library"
            "could not be loaded."
        )

    modules = {}
    package_name = "indy_vdr"
    modules[package_name] = mock.MagicMock()
    return Stub(mock.patch.dict(sys.modules, modules))


def stub_ursa_bbs_signatures() -> Stub:
    # detect ursa_bbs_signatures library
    try:
        from ursa_bbs_signatures._ffi.ffi_util import get_library

        get_library()
        return Stub(None)
    except ImportError:
        print(
            "Skipping Ursa-BBS-Signatures-specific tests:"
            " ursa_bbs_signatures module not installed."
        )
    except (OSError, Exception):
        print(
            "Skipping Ursa-BBS-Signatures-specific tests: bbs shared library "
            "could not be loaded."
        )

    modules = {}
    package_name = "ursa_bbs_signatures"
    modules[package_name] = mock.MagicMock()
    # Temporary until ursa_bbs_signatures is updated to export the FfiException
    # from the main package
    modules[package_name + "._ffi.FfiException"] = mock.MagicMock()
    return Stub(mock.patch.dict(sys.modules, modules))


def pytest_sessionstart(session):
    global STUBS, POSTGRES_URL, ENABLE_PTVSD
    args = sys.argv
    
    # copied from __main__.py:init_debug
    ENABLE_PTVSD = os.getenv("ENABLE_PTVSD", "").lower()
    ENABLE_PTVSD = ENABLE_PTVSD and ENABLE_PTVSD not in ("false", "0")

    # --debug to use microsoft's visual studio remote debugger
    if ENABLE_PTVSD or "--debug" in args:
        DAP_HOST = os.getenv("PTVSD_HOST", None) or os.getenv("DAP_HOST", "localhost")
        DAP_PORT = os.getenv("PTVSD_PORT", None) or os.getenv("DAP_PORT", 5678)
        try:
            import debugpy

            debugpy.listen((DAP_HOST, DAP_PORT))
            print(f"=== Waiting for debugger to attach to {DAP_HOST}:{DAP_PORT} ===")
            debugpy.wait_for_client()
        except ImportError:
            print("debugpy library was not found")

    POSTGRES_URL = os.getenv("POSTGRES_URL")

    STUBS.update(
        {
            "anoncreds": stub_anoncreds(),
            "askar": stub_askar(),
            "indy_credx": stub_indy_credx(),
            "indy_vdr": stub_indy_vdr(),
            "ursa_bbs_signatures": stub_ursa_bbs_signatures(),
        }
    )
    for stub in STUBS.values():
        stub.start()


def pytest_sessionfinish(session):
    global STUBS

    for stub in STUBS.values():
        stub.stop()
    STUBS.clear()


def pytest_runtest_setup(item: pytest.Item):
    global STUBS

    if tuple(item.iter_markers(name="anoncreds")) and not STUBS["anoncreds"].found:
        pytest.skip("test requires Anoncreds support")

    if tuple(item.iter_markers(name="askar")) and not STUBS["askar"].found:
        pytest.skip("test requires Askar support")

    if tuple(item.iter_markers(name="indy")) and not STUBS["indy"].found:
        pytest.skip("test requires Indy support")

    if tuple(item.iter_markers(name="indy_credx")) and not STUBS["indy_credx"].found:
        pytest.skip("test requires Indy-Credx support")

    if tuple(item.iter_markers(name="indy_vdr")) and not STUBS["indy_vdr"].found:
        pytest.skip("test requires Indy-VDR support")

    if (
        tuple(item.iter_markers(name="ursa_bbs_signatures"))
        and not STUBS["ursa_bbs_signatures"].found
    ):
        pytest.skip("test requires Ursa-BBS-Signatures support")

    if tuple(item.iter_markers(name="postgres")) and not POSTGRES_URL:
        pytest.skip("test requires Postgres support")
