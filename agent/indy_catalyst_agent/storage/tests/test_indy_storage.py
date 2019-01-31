import pytest

_indy = pytest.importorskip("indy")

from indy_catalyst_agent.wallet.indy import IndyWallet
from indy_catalyst_agent.storage.indy import IndyStorage

from . import test_basic_storage

@pytest.fixture()
async def store():
    wallet = IndyWallet({
        "auto_create": True,
        "auto_remove": True,
        "name": "test-wallet",
        "seed": "testseed00000000000000000000skip",
    })
    await wallet.open()
    yield IndyStorage(wallet)
    await wallet.close()


class TestIndyStorage(test_basic_storage.TestBasicStorage):
    pass
