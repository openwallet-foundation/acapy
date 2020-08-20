from asynctest import TestCase as AsyncTestCase
import pytest

from ...config.settings import Settings
from ..error import WalletError
from .. import provider as test_module


class TestProvider(AsyncTestCase):
    async def test_provide_basic(self):
        provider = test_module.WalletProvider()
        settings = Settings(
            values={
                "wallet.type": "basic",
                "wallet.key": "key",
                "wallet.name": "name",
                "wallet.storage_type": "storage_type",
                "wallet.storage_config": "storage_config",
                "wallet.storage_creds": "storage_creds",
            }
        )
        wallet = await provider.provide(settings, None)

        assert wallet.opened
        assert wallet.name == "name"
        await wallet.close()

    @pytest.mark.indy
    async def test_provide_indy(self):
        provider = test_module.WalletProvider()
        settings = Settings(
            values={"wallet.type": "indy", "wallet.key": "key", "wallet.name": "name",}
        )
        wallet = await provider.provide(settings, None)

        assert wallet.opened
        assert wallet.name == "name"
        await wallet.close()
        assert not wallet.opened

        settings["wallet.rekey"] = "rekey"
        assert settings["wallet.rekey"] == "rekey"

        wallet = await provider.provide(settings, None)
        assert wallet.opened

        await wallet.close()
        assert not wallet.opened

        with pytest.raises(WalletError):  # make sure old key does not work
            wallet = await provider.provide(settings, None)

        settings["wallet.key"] = "rekey"
        del settings["wallet.rekey"]

        wallet = await provider.provide(settings, None)
        assert wallet.opened
        await wallet.close()
