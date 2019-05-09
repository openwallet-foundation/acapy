import json
from unittest import mock

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from indy_catalyst_agent.ledger.indy import IndyLedger


class TestIndyLedger(AsyncTestCase):
    def test_init(self):
        ledger = IndyLedger("name", "wallet", "genesis_transactions")

        assert ledger.name == "name"
        assert ledger.wallet == "wallet"
