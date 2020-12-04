import pytest
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.connections.models.connection_record import (
    ConnectionRecord
)
from aries_cloudagent.messaging.request_context import RequestContext
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.basic import BasicStorage
from aries_cloudagent.transport.inbound.receipt import MessageReceipt
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.wallet.basic import BasicWallet

from ....routing.v1_0.manager import RoutingManager
from ..manager import MediationManager, MediationManagerError
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.mediate_request import MediationRequest
from ..models.mediation_record import MediationRecord

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestMediationManager(AsyncTestCase):
    async def setUp(self):
        self.context = RequestContext(
            base_context=InjectionContext(enforce_typing=False)
        )
        self.context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
        self.context.connection_record = ConnectionRecord(connection_id=TEST_CONN_ID)
        self.storage = BasicStorage()
        self.wallet = BasicWallet()
        self.context.injector.bind_instance(BaseStorage, self.storage)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.manager = MediationManager(self.context)
        self.record = MediationRecord(connection_id=TEST_CONN_ID)
        assert self.manager.context

    async def test_create_manager_no_context(self):
        with self.assertRaises(MediationManagerError):
            await MediationManager(None)

    async def test_create_did(self):
        await self.manager._create_routing_did()
        assert await self.manager._retrieve_routing_did()

    async def test_retrieve_did_when_absent(self):
        assert await self.manager._retrieve_routing_did() is None

    async def test_receive_request_no_terms(self):
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID

    @pytest.mark.skip(
        reason='mediator and recipient terms are only loosely defined in RFC 0211'
    )
    async def test_receive_request_unacceptable_terms(self):
        pass

    async def test_grant_request(self):
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID
        grant = await self.manager.grant_request(record)
        assert grant.endpoint == self.context.settings.get("default_endpoint")
        assert grant.routing_keys == [(await self.manager._retrieve_routing_did()).verkey]

    async def test_deny_request(self):
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID
        deny = await self.manager.deny_request(record)
        assert deny.mediator_terms == []
        assert deny.recipient_terms == []

    async def test_update_keylist_delete(self):
        routing_mgr = RoutingManager(self.context)
        await routing_mgr.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_ROUTE_VERKEY, action=KeylistUpdateRule.RULE_REMOVE
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_REMOVE
        assert results[0].result == KeylistUpdated.RESULT_SUCCESS

    async def test_update_keylist_create(self):
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_ROUTE_VERKEY, action=KeylistUpdateRule.RULE_ADD
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_ADD
        assert results[0].result == KeylistUpdated.RESULT_SUCCESS

    async def test_update_keylist_create_existing(self):
        routing_mgr = RoutingManager(self.context)
        await routing_mgr.create_route_record(TEST_CONN_ID, TEST_ROUTE_VERKEY)
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_ROUTE_VERKEY, action=KeylistUpdateRule.RULE_ADD
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_ROUTE_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_ADD
        assert results[0].result == KeylistUpdated.RESULT_NO_CHANGE

    async def test_get_keylist(self):
        routing_mgr = RoutingManager(self.context)
        await routing_mgr.create_route_record(
            TEST_CONN_ID, TEST_ROUTE_VERKEY
        )
        results = await self.manager.get_keylist(self.record)
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_ROUTE_VERKEY

    async def test_create_keylist_query_response(self):
        routing_mgr = RoutingManager(self.context)
        await routing_mgr.create_route_record(
            TEST_CONN_ID, TEST_ROUTE_VERKEY
        )
        results = await self.manager.get_keylist(self.record)
        response = await self.manager.create_keylist_query_response(results)
        assert len(response.keys) == 1
        assert response.keys[0].recipient_key
        response = await self.manager.create_keylist_query_response([])
        assert not response.keys
