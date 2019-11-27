from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ......cache.base import BaseCache
from ......cache.basic import BasicCache
from ......config.injection_context import InjectionContext
from ......messaging.request_context import RequestContext
from ......storage.base import BaseStorage
from ......storage.basic import BasicStorage

from ..credential_exchange import V10CredentialExchange


class TestCredentialExchange(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )

        self.cache = BasicCache()
        self.context.injector.bind_instance(BaseCache, self.cache)

        self.storage = BasicStorage()
        self.context.injector.bind_instance(BaseStorage, self.storage)

    async def test_retrieve_by_connection_and_thread(self):
        records = [
            V10CredentialExchange(
                connection_id=str(i),
                thread_id=str(i),
            ) for i in range(3)
        ]
        for record in records:
            await record.save(self.context)

        for i in range(2):  # cover cache code for both set() and get()
            found = await V10CredentialExchange.retrieve_by_connection_and_thread(
                context=self.context,
                connection_id=str(1),
                thread_id=str(1),
            )
            assert found.serialize() == records[1].serialize()
