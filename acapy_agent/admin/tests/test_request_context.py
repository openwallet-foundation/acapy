from unittest import IsolatedAsyncioTestCase

from ...askar.profile import AskarProfileSession
from ...utils.stats import Collector
from ...utils.testing import create_test_profile
from .. import request_context as test_module


class TestAdminRequestContext(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        self.ctx = test_module.AdminRequestContext(self.profile)
        assert self.ctx.__class__.__name__ in str(self.ctx)

        self.ctx_with_added_attrs = test_module.AdminRequestContext(
            profile=self.profile,
            metadata={"test_attrib_key": "test_attrib_value"},
        )
        assert self.ctx_with_added_attrs.__class__.__name__ in str(
            self.ctx_with_added_attrs
        )

    def test_session_transaction(self):
        sesn = self.ctx.session()
        assert isinstance(sesn, AskarProfileSession)
        txn = self.ctx.transaction()
        assert isinstance(txn, AskarProfileSession)

        sesn = self.ctx_with_added_attrs.session()
        assert isinstance(sesn, AskarProfileSession)
        txn = self.ctx_with_added_attrs.transaction()
        assert isinstance(txn, AskarProfileSession)

    async def test_session_inject_x(self):
        test_ctx = test_module.AdminRequestContext(self.profile)
        async with test_ctx.session() as session:
            with self.assertRaises(test_module.InjectionError):
                session.inject(Collector)
