from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from collections import OrderedDict

from ....core.in_memory import InMemoryProfile
from ....messaging.responder import BaseResponder

from ..indy_manager import MultiIndyLedgerManager


class TestMultiIndyLedgerManager(AsyncTestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.context = self.profile.context

        self.responder = async_mock.CoroutineMock(send=async_mock.CoroutineMock())
        self.context.injector.bind_instance(BaseResponder, self.responder)
        self.production_ledger = OrderedDict()
        self.non_production_ledger = OrderedDict()
        self.manager = MultiIndyLedgerManager(self.profile)
