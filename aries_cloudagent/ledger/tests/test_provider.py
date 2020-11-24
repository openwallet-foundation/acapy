from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from ...config.injection_context import InjectionContext
from ...ledger.pool.base import BaseLedgerPool
from ...ledger.indy import IndyLedger
from ...wallet.base import BaseWallet

from ..provider import LedgerProvider

from aries_cloudagent.ledger.indy import IndyLedger


@pytest.mark.indy
class TestProvider(AsyncTestCase):
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

    async def test_provide(self):
        provider = LedgerProvider()

        context = InjectionContext(enforce_typing=False)

        mock_wallet = async_mock.MagicMock()
        mock_wallet.type = "indy"

        mock_pool = async_mock.MagicMock()
        mock_pool.name = "name"

        context.injector.bind_instance(BaseWallet, mock_wallet)
        context.injector.bind_instance(BaseLedgerPool, mock_pool)

        result = await provider.provide(
            settings={
                "ledger.read_only": True,
            },
            injector=context.injector,
        )
        assert isinstance(result, IndyLedger)
        assert result.pool.name == "name"
