from asynctest import TestCase as AsyncTestCase
import pytest

from ...config.settings import Settings
from .. import provider as test_module


class TestProvider(AsyncTestCase):
    async def test_provide(self):
        provider = test_module.WalletProvider()
        settings = Settings(
            values={
                "wallet.type": "basic",
                "wallet.key": "key",
                "wallet.name": "name",
                "wallet.storage_type": "storage_type",
                "wallet.storage_config": "storage_config",
                "wallet.storage_creds": "storage_creds"
            }
        )
        wallet = await provider.provide(settings, None)

        assert wallet.name == "name"
