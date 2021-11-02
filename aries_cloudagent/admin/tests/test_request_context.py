from asynctest import mock as asyn_mock, TestCase as AsyncTestCase

from ...core.in_memory import InMemoryProfile
from ...core.profile import ProfileSession
from ...utils.stats import Collector

from .. import request_context as test_module


class TestAdminRequestContext(AsyncTestCase):
    def setUp(self):
        self.ctx = test_module.AdminRequestContext(InMemoryProfile.test_profile())
        assert self.ctx.__class__.__name__ in str(self.ctx)

    def test_session_transaction(self):
        sesn = self.ctx.session()
        assert isinstance(sesn, ProfileSession)
        txn = self.ctx.transaction()
        assert isinstance(txn, ProfileSession)

    async def test_session_inject_x(self):
        test_ctx = test_module.AdminRequestContext.test_context({Collector: None})
        async with test_ctx.session() as test_sesn:
            with self.assertRaises(test_module.InjectionError):
                test_sesn.inject(Collector)
