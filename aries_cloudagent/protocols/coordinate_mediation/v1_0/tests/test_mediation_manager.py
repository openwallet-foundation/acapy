"""Test MediationManager."""
import pytest

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

from ....routing.v1_0.models.route_record import RouteRecord
from ..manager import (
    MediationAlreadyExists, MediationManager, MediationManagerError
)
from ..messages.inner.keylist_update_rule import KeylistUpdateRule
from ..messages.inner.keylist_updated import KeylistUpdated
from ..messages.mediate_deny import MediationDeny
from ..messages.mediate_grant import MediationGrant
from ..messages.mediate_request import MediationRequest
from ..models.mediation_record import MediationRecord

TEST_CONN_ID = "conn-id"
TEST_ENDPOINT = "https://example.com"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ROUTE_VERKEY = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"


class TestMediationManager(AsyncTestCase):  # pylint: disable=R0904
    """Test MediationManager."""

    async def setUp(self):  # pylint: disable=C0103
        """setUp."""
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
        self.record = MediationRecord(
            state=MediationRecord.STATE_GRANTED,
            connection_id=TEST_CONN_ID
        )
        assert self.manager.context

    async def test_create_manager_no_context(self):
        """test_create_manager_no_context."""
        with self.assertRaises(MediationManagerError):
            await MediationManager(None)

    async def test_create_did(self):
        """test_create_did."""
        # pylint: disable=W0212
        await self.manager._create_routing_did()
        assert await self.manager._retrieve_routing_did()

    async def test_retrieve_did_when_absent(self):
        """test_retrieve_did_when_absent."""
        # pylint: disable=W0212
        assert await self.manager._retrieve_routing_did() is None

    async def test_receive_request_no_terms(self):
        """test_receive_request_no_terms."""
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID

    async def test_receive_request_record_exists(self):
        """test_receive_request_no_terms."""
        request = MediationRequest()
        await MediationRecord(connection_id=TEST_CONN_ID).save(self.context)
        with pytest.raises(MediationAlreadyExists):
            await self.manager.receive_request(request)

    @pytest.mark.skip(
        reason='mediator and recipient terms are only loosely defined in RFC 0211'
    )
    async def test_receive_request_unacceptable_terms(self):
        """test_receive_request_unacceptable_terms."""

    async def test_grant_request(self):
        """test_grant_request."""
        # pylint: disable=W0212
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID
        grant = await self.manager.grant_request(record)
        assert grant.endpoint == self.context.settings.get("default_endpoint")
        assert grant.routing_keys == [(await self.manager._retrieve_routing_did()).verkey]

    async def test_deny_request(self):
        """test_deny_request."""
        request = MediationRequest()
        record = await self.manager.receive_request(request)
        assert record.connection_id == TEST_CONN_ID
        deny = await self.manager.deny_request(record)
        assert deny.mediator_terms == []
        assert deny.recipient_terms == []

    async def test_update_keylist_delete(self):
        """test_update_keylist_delete."""
        await RouteRecord(
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_VERKEY, action=KeylistUpdateRule.RULE_REMOVE
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_REMOVE
        assert results[0].result == KeylistUpdated.RESULT_SUCCESS

    async def test_update_keylist_create(self):
        """test_update_keylist_create."""
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_VERKEY, action=KeylistUpdateRule.RULE_ADD
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_ADD
        assert results[0].result == KeylistUpdated.RESULT_SUCCESS

    async def test_update_keylist_create_existing(self):
        """test_update_keylist_create_existing."""
        await RouteRecord(
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        response = await self.manager.update_keylist(
            record=self.record,
            updates=[
                KeylistUpdateRule(
                    recipient_key=TEST_VERKEY, action=KeylistUpdateRule.RULE_ADD
                )
            ],
        )
        results = response.updated
        assert len(results) == 1
        assert results[0].recipient_key == TEST_VERKEY
        assert results[0].action == KeylistUpdateRule.RULE_ADD
        assert results[0].result == KeylistUpdated.RESULT_NO_CHANGE

    async def test_get_keylist(self):
        """test_get_keylist."""
        await RouteRecord(
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        # Non-server route for verifying filtering
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_ROUTE_VERKEY
        ).save(self.context)
        results = await self.manager.get_keylist(self.record)
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_VERKEY

    async def test_create_keylist_query_response(self):
        """test_create_keylist_query_response."""
        await RouteRecord(
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        results = await self.manager.get_keylist(self.record)
        response = await self.manager.create_keylist_query_response(results)
        assert len(response.keys) == 1
        assert response.keys[0].recipient_key
        response = await self.manager.create_keylist_query_response([])
        assert not response.keys

    async def test_prepare_request(self):
        """test_prepare_request."""
        record, request = await self.manager.prepare_request(TEST_CONN_ID)
        assert record.connection_id == TEST_CONN_ID
        assert request

    async def test_request_granted(self):
        """test_request_granted."""
        record, _ = await self.manager.prepare_request(TEST_CONN_ID)
        grant = MediationGrant(endpoint=TEST_ENDPOINT, routing_keys=[TEST_ROUTE_VERKEY])
        await self.manager.request_granted(record, grant)
        assert record.state == MediationRecord.STATE_GRANTED
        assert record.endpoint == TEST_ENDPOINT
        assert record.routing_keys == [TEST_ROUTE_VERKEY]

    async def test_request_denied(self):
        """test_request_denied."""
        record, _ = await self.manager.prepare_request(TEST_CONN_ID)
        deny = MediationDeny()
        await self.manager.request_denied(record, deny)
        assert record.state == MediationRecord.STATE_DENIED

    @pytest.mark.skip(reason='Mediation terms are not well defined in RFC 0211')
    async def test_request_denied_counter_terms(self):
        """test_request_denied_counter_terms."""

    async def test_prepare_keylist_query(self):
        """test_prepare_keylist_query."""
        query = await self.manager.prepare_keylist_query()
        assert query.paginate.limit == -1
        assert query.paginate.offset == 0

    async def test_prepare_keylist_query_pagination(self):
        """test_prepare_keylist_query_pagination."""
        query = await self.manager.prepare_keylist_query(
            paginate_limit=10,
            paginate_offset=20
        )
        assert query.paginate.limit == 10
        assert query.paginate.offset == 20

    @pytest.mark.skip(reason='Filtering is not well defined in RFC 0211')
    async def test_prepare_keylist_query_filter(self):
        """test_prepare_keylist_query_filter."""

    async def test_add_key_no_message(self):
        """test_add_key_no_message."""
        update = await self.manager.add_key(TEST_VERKEY)
        assert update.updates
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD

    async def test_add_key_accumulate_in_message(self):
        """test_add_key_accumulate_in_message."""
        update = await self.manager.add_key(TEST_VERKEY)
        await self.manager.add_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[1].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_remove_key_no_message(self):
        """test_remove_key_no_message."""
        update = await self.manager.remove_key(TEST_VERKEY)
        assert update.updates
        assert update.updates[0].action == KeylistUpdateRule.RULE_REMOVE

    async def test_remove_key_accumulate_in_message(self):
        """test_remove_key_accumulate_in_message."""
        update = await self.manager.remove_key(TEST_VERKEY)
        await self.manager.remove_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[1].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_add_remove_key_mix(self):
        """test_add_remove_key_mix."""
        update = await self.manager.add_key(TEST_VERKEY)
        await self.manager.remove_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[1].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_get_my_keylist(self):
        """test_get_my_keylist."""
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY
        ).save(self.context)
        # Non-client record to verify filtering
        await RouteRecord(
            role=RouteRecord.ROLE_SERVER,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_ROUTE_VERKEY
        ).save(self.context)
        keylist = await self.manager.get_my_keylist(TEST_CONN_ID)
        assert keylist
        assert len(keylist) == 1
        assert keylist[0].connection_id == TEST_CONN_ID
        assert keylist[0].recipient_key == TEST_VERKEY
        assert keylist[0].role == RouteRecord.ROLE_CLIENT
