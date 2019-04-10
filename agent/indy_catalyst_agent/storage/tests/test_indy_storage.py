import pytest

try:
    from indy.libindy import _cdll

    _cdll()
except ImportError:
    pytest.skip(
        "skipping Indy-specific tests: python module not installed",
        allow_module_level=True,
    )
except OSError:
    pytest.skip(
        "skipping Indy-specific tests: shared library not loaded",
        allow_module_level=True,
    )

from indy_catalyst_agent.wallet.indy import IndyWallet
from indy_catalyst_agent.storage.indy import IndyStorage

from . import test_basic_storage


@pytest.fixture()
async def store():
    wallet = IndyWallet(
        {"auto_create": True, "auto_remove": True, "name": "test-wallet"}
    )
    await wallet.open()
    yield IndyStorage(wallet)
    await wallet.close()


class TestIndyStorage(test_basic_storage.TestBasicStorage):
    """ """

    pass
