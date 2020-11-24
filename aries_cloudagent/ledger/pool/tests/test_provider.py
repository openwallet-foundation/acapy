from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from ....config.injection_context import InjectionContext

from ..provider import LedgerPoolProvider

from aries_cloudagent.ledger.pool.indy import IndyLegderPool


@pytest.mark.indy
class TestProvider(AsyncTestCase):
    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("builtins.open")
    async def test_provide(
        self,
        mock_open,
        mock_create_ledger_config,
    ):
        mock_open.return_value = async_mock.MagicMock()
        provider = LedgerPoolProvider()

        context = InjectionContext(enforce_typing=False)

        result = await provider.provide(
            settings={
                "ledger.pool_name": "name",
                "ledger.genesis_transactions": "dummy",
                "wallet.type": "indy",
            },
            injector=context.injector,
        )
        assert isinstance(result, IndyLegderPool)
        assert result.name == "name"

    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_provide_no_pool_config(self, mock_open, mock_list_pools):
        mock_open.return_value = async_mock.MagicMock()
        provider = LedgerPoolProvider()

        mock_list_pools.return_value = []

        context = InjectionContext(enforce_typing=False)

        result = await provider.provide(
            settings={"ledger.pool_name": "name", "wallet.type": "indy"},
            injector=context.injector,
        )
        assert result is None

    async def test_provide_wallet_type_not_indy(self):
        provider = LedgerPoolProvider()

        context = InjectionContext(enforce_typing=False)

        result = await provider.provide(
            settings={"ledger.pool_name": "name", "wallet.type": "basic"},
            injector=context.injector,
        )
        assert result is None
