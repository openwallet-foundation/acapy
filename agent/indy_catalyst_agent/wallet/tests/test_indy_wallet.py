import pytest

_indy = pytest.importorskip("indy")

from indy_catalyst_agent.wallet.basic import BasicWallet
from indy_catalyst_agent.wallet.indy import IndyWallet

from . import test_basic_wallet


@pytest.fixture()
def basic_wallet():
    yield BasicWallet()

@pytest.fixture()
def wallet():
    yield IndyWallet({
        "auto_create": True,
        "auto_remove": True,
        "name": "test-wallet",
        "seed": "testseed00000000000000000000skip",
    })


class TestIndyWallet(test_basic_wallet.TestBasicWallet):

    # all basic wallet tests included

    @pytest.mark.asyncio
    async def test_compare_pack(self, basic_wallet, wallet):
        """
        Ensure that python-based pack/unpack is compatible with indy-sdk implementation
        """
        await basic_wallet.open()
        await basic_wallet.create_local_did(self.test_seed)
        py_packed = await basic_wallet.pack_message(
            self.test_message,
            [self.test_verkey],
            self.test_verkey,
        )

        await wallet.open()
        try:
            await wallet.create_local_did(self.test_seed)
            packed = await wallet.pack_message(
                self.test_message,
                [self.test_verkey],
                self.test_verkey,
            )

            py_unpacked, from_vk, to_vk = await basic_wallet.unpack_message(packed)
            assert self.test_message == py_unpacked

            unpacked, from_vk, to_vk = await wallet.unpack_message(py_packed)
            assert self.test_message == unpacked
        finally:
            await wallet.close()
        await basic_wallet.close()
