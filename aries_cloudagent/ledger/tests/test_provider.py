from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import json
import pytest

from ...config.injection_context import InjectionContext
from ...ledger.base import BaseLedger
from ...ledger.indy import GENESIS_TRANSACTION_PATH, IndyLedger
from ...wallet.base import BaseWallet

from ..provider import LedgerProvider

from aries_cloudagent.ledger.indy import IndyLedger


@pytest.mark.indy
class TestProvider(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

    @async_mock.patch("indy.pool.create_pool_ledger_config")
    @async_mock.patch("builtins.open")
    async def test_provide(
        self,
        mock_open,
        mock_create_ledger_config,
    ):
        mock_open.return_value = async_mock.MagicMock()
        provider = LedgerProvider()

        context = InjectionContext(enforce_typing=False)
        mock_wallet = async_mock.MagicMock()
        mock_wallet.type = "indy"
        context.injector.bind_instance(BaseWallet, mock_wallet)

        result = provider.provide(
            settings={
                "ledger.pool_name": "name",
                "ledger.genesis_transactions": "dummy",
                "ledger.read_only": True,
            },
            injector=context.injector,
        )
        assert isinstance(result, IndyLedger)
        assert result.pool_name == "name"

    @async_mock.patch("indy.pool.list_pools")
    @async_mock.patch("builtins.open")
    async def test_provide_no_pool_config(self, mock_open, mock_list_pools):
        mock_open.return_value = async_mock.MagicMock()
        provider = LedgerProvider()

        mock_list_pools.return_value = []

        context = InjectionContext(enforce_typing=False)
        mock_wallet = async_mock.MagicMock()
        mock_wallet.type = "indy"
        context.injector.bind_instance(BaseWallet, mock_wallet)

        result = provider.provide(
            settings={
                "ledger.pool_name": "name",
            },
            injector=context.injector,
        )
        assert result is None
