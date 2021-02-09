"""Test MediationManager."""
import logging

import pytest

from asynctest import mock as async_mock

from .....core.profile import Profile, ProfileSession
from .....connections.models.conn_record import ConnRecord
from .....messaging.request_context import RequestContext
from .....storage.error import StorageNotFoundError
from .....transport.inbound.receipt import MessageReceipt

from ....routing.v1_0.models.route_record import RouteRecord

from .. import manager as test_module
from ..manager import (
    MediationAlreadyExists,
    MediationManager,
    MediationManagerError,
    MediationNotGrantedError,
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

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def profile() -> Profile:
    """Fixture for profile used in tests."""
    # pylint: disable=W0621
    context = RequestContext.test_context()
    context.message_receipt = MessageReceipt(sender_verkey=TEST_VERKEY)
    context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)
    yield context.profile


@pytest.fixture
async def session(profile) -> ProfileSession:  # pylint: disable=W0621
    """Fixture for profile session used in tests."""
    yield await profile.session()


@pytest.fixture
async def manager(profile) -> MediationManager:  # pylint: disable=W0621
    """Fixture for manager used in tests."""
    yield MediationManager(profile)


@pytest.fixture
def record() -> MediationRecord:
    """Fixture for record used in tests."""
    yield MediationRecord(
        state=MediationRecord.STATE_GRANTED, connection_id=TEST_CONN_ID
    )


class TestMediationManager:  # pylint: disable=R0904,W0621
    """Test MediationManager."""

    async def test_create_manager_no_profile(self):
        """test_create_manager_no_profile."""
        with pytest.raises(MediationManagerError):
            await MediationManager(None)

    async def test_create_did(self, manager, session):
        """test_create_did."""
        # pylint: disable=W0212
        await manager._create_routing_did(session)
        assert await manager._retrieve_routing_did(session)

    async def test_retrieve_did_when_absent(self, manager, session):
        """test_retrieve_did_when_absent."""
        # pylint: disable=W0212
        assert await manager._retrieve_routing_did(session) is None

    async def test_receive_request_no_terms(self, manager):
        """test_receive_request_no_terms."""
        request = MediationRequest()
        record = await manager.receive_request(TEST_CONN_ID, request)
        assert record.connection_id == TEST_CONN_ID

    async def test_receive_request_record_exists(self, session, manager):
        """test_receive_request_no_terms."""
        request = MediationRequest()
        await MediationRecord(connection_id=TEST_CONN_ID).save(session)
        with pytest.raises(MediationAlreadyExists):
            await manager.receive_request(TEST_CONN_ID, request)

    @pytest.mark.skip(
        reason="mediator and recipient terms are only loosely defined in RFC 0211"
    )
    async def test_receive_request_unacceptable_terms(self):
        """test_receive_request_unacceptable_terms."""

    async def test_grant_request(self, session, manager):
        """test_grant_request."""
        # pylint: disable=W0212
        request = MediationRequest()
        record = await manager.receive_request(TEST_CONN_ID, request)
        assert record.connection_id == TEST_CONN_ID
        record, grant = await manager.grant_request(record.mediation_id)
        assert grant.endpoint == session.settings.get("default_endpoint")
        assert grant.routing_keys == [
            (await manager._retrieve_routing_did(session)).verkey
        ]

    async def test_deny_request(self, manager):
        """test_deny_request."""
        request = MediationRequest()
        record = await manager.receive_request(TEST_CONN_ID, request)
        assert record.connection_id == TEST_CONN_ID
        record, deny = await manager.deny_request(record.mediation_id)
        assert deny.mediator_terms == []
        assert deny.recipient_terms == []

    async def test_update_keylist_delete(self, session, manager, record):
        """test_update_keylist_delete."""
        await RouteRecord(connection_id=TEST_CONN_ID, recipient_key=TEST_VERKEY).save(
            session
        )
        response = await manager.update_keylist(
            record=record,
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

    async def test_update_keylist_create(self, manager, record):
        """test_update_keylist_create."""
        response = await manager.update_keylist(
            record=record,
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

    async def test_update_keylist_create_existing(self, session, manager, record):
        """test_update_keylist_create_existing."""
        await RouteRecord(connection_id=TEST_CONN_ID, recipient_key=TEST_VERKEY).save(
            session
        )
        response = await manager.update_keylist(
            record=record,
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

    async def test_update_keylist_x_not_granted(
        self, manager: MediationManager, record: MediationRecord
    ):
        record.state = MediationRecord.STATE_DENIED
        with pytest.raises(MediationNotGrantedError):
            await manager.update_keylist(record, [])

    async def test_get_keylist(self, session, manager, record):
        """test_get_keylist."""
        await RouteRecord(connection_id=TEST_CONN_ID, recipient_key=TEST_VERKEY).save(
            session
        )
        # Non-server route for verifying filtering
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_ROUTE_VERKEY,
        ).save(session)
        results = await manager.get_keylist(record)
        assert len(results) == 1
        assert results[0].connection_id == TEST_CONN_ID
        assert results[0].recipient_key == TEST_VERKEY

    async def test_get_keylist_no_granted_record(self, manager):
        """test_get_keylist_no_granted_record."""
        record = MediationRecord()
        with pytest.raises(MediationNotGrantedError):
            await manager.get_keylist(record)

    async def test_mediation_record_eq(self):
        record_0 = MediationRecord(endpoint="zero")
        record_1 = MediationRecord(endpoint="one")
        assert record_0 != record_1
        assert record_0 != ValueError("not a mediation record")

        with pytest.raises(ValueError):
            record_0.state = "bad state"

    async def test_mediation_record_duplicate_means_exists(self, session):
        await MediationRecord(connection_id=TEST_CONN_ID, endpoint="abc").save(session)
        await MediationRecord(connection_id=TEST_CONN_ID, endpoint="def").save(session)
        assert await MediationRecord.exists_for_connection_id(session, TEST_CONN_ID)

    async def test_create_keylist_query_response(self, session, manager, record):
        """test_create_keylist_query_response."""
        await RouteRecord(connection_id=TEST_CONN_ID, recipient_key=TEST_VERKEY).save(
            session
        )
        results = await manager.get_keylist(record)
        response = await manager.create_keylist_query_response(results)
        assert len(response.keys) == 1
        assert response.keys[0].recipient_key
        response = await manager.create_keylist_query_response([])
        assert not response.keys

    async def test_get_set_get_default_mediator(
        self,
        session: ProfileSession,
        manager: MediationManager,
        record: MediationRecord,
    ):
        await record.save(session)
        assert await manager.get_default_mediator() == None
        await manager.set_default_mediator(record)
        assert await manager.get_default_mediator() == record

    async def test_set_get_default_mediator_by_id(
        self, manager: MediationManager, session
    ):
        await manager._set_default_mediator_id("test", session)
        assert await manager.get_default_mediator_id() == "test"

    async def test_set_set_get_default_mediator_by_id(
        self, manager: MediationManager, session
    ):
        await manager._set_default_mediator_id("test", session)
        await manager._set_default_mediator_id("updated", session)
        assert await manager.get_default_mediator_id() == "updated"

    async def test_clear_default_mediator(self, manager: MediationManager, session):
        await manager._set_default_mediator_id("test", session)
        assert await manager.get_default_mediator_id()
        await manager.clear_default_mediator()
        assert not await manager.get_default_mediator_id()

    async def test_clear_default_mediator_no_default_set(
        self, manager: MediationManager
    ):
        await manager.clear_default_mediator()

    async def test_prepare_request(self, manager):
        """test_prepare_request."""
        record, request = await manager.prepare_request(TEST_CONN_ID)
        assert record.connection_id == TEST_CONN_ID
        assert request

    async def test_request_granted(self, manager):
        """test_request_granted."""
        record, _ = await manager.prepare_request(TEST_CONN_ID)
        grant = MediationGrant(endpoint=TEST_ENDPOINT, routing_keys=[TEST_ROUTE_VERKEY])
        await manager.request_granted(record, grant)
        assert record.state == MediationRecord.STATE_GRANTED
        assert record.endpoint == TEST_ENDPOINT
        assert record.routing_keys == [TEST_ROUTE_VERKEY]

    async def test_request_denied(self, manager):
        """test_request_denied."""
        record, _ = await manager.prepare_request(TEST_CONN_ID)
        deny = MediationDeny()
        await manager.request_denied(record, deny)
        assert record.state == MediationRecord.STATE_DENIED

    @pytest.mark.skip(reason="Mediation terms are not well defined in RFC 0211")
    async def test_request_denied_counter_terms(self):
        """test_request_denied_counter_terms."""

    async def test_prepare_keylist_query(self, manager):
        """test_prepare_keylist_query."""
        query = await manager.prepare_keylist_query()
        assert query.paginate.limit == -1
        assert query.paginate.offset == 0

    async def test_prepare_keylist_query_pagination(self, manager):
        """test_prepare_keylist_query_pagination."""
        query = await manager.prepare_keylist_query(
            paginate_limit=10, paginate_offset=20
        )
        assert query.paginate.limit == 10
        assert query.paginate.offset == 20

    @pytest.mark.skip(reason="Filtering is not well defined in RFC 0211")
    async def test_prepare_keylist_query_filter(self):
        """test_prepare_keylist_query_filter."""

    async def test_add_key_no_message(self, manager):
        """test_add_key_no_message."""
        update = await manager.add_key(TEST_VERKEY)
        assert update.updates
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD

    async def test_add_key_accumulate_in_message(self, manager):
        """test_add_key_accumulate_in_message."""
        update = await manager.add_key(TEST_VERKEY)
        await manager.add_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[1].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_remove_key_no_message(self, manager):
        """test_remove_key_no_message."""
        update = await manager.remove_key(TEST_VERKEY)
        assert update.updates
        assert update.updates[0].action == KeylistUpdateRule.RULE_REMOVE

    async def test_remove_key_accumulate_in_message(self, manager):
        """test_remove_key_accumulate_in_message."""
        update = await manager.remove_key(TEST_VERKEY)
        await manager.remove_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[1].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_add_remove_key_mix(self, manager):
        """test_add_remove_key_mix."""
        update = await manager.add_key(TEST_VERKEY)
        await manager.remove_key(recipient_key=TEST_ROUTE_VERKEY, message=update)
        assert update.updates
        assert len(update.updates) == 2
        assert update.updates[0].action == KeylistUpdateRule.RULE_ADD
        assert update.updates[1].action == KeylistUpdateRule.RULE_REMOVE
        assert update.updates[0].recipient_key == TEST_VERKEY
        assert update.updates[1].recipient_key == TEST_ROUTE_VERKEY

    async def test_store_update_results(self, session, manager):
        """test_store_update_results."""
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY,
        ).save(session)
        results = [
            KeylistUpdated(
                recipient_key=TEST_ROUTE_VERKEY,
                action=KeylistUpdateRule.RULE_ADD,
                result=KeylistUpdated.RESULT_SUCCESS,
            ),
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_REMOVE,
                result=KeylistUpdated.RESULT_SUCCESS,
            ),
        ]
        await manager.store_update_results(TEST_CONN_ID, results)
        routes = await RouteRecord.query(session)

        assert len(routes) == 1
        assert routes[0].recipient_key == TEST_ROUTE_VERKEY

        results = [
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_REMOVE,
                result=KeylistUpdated.RESULT_SUCCESS,
            ),
        ]

        with async_mock.patch.object(
            RouteRecord, "query", async_mock.CoroutineMock()
        ) as mock_route_rec_query, async_mock.patch.object(
            test_module.LOGGER, "error", async_mock.MagicMock()
        ) as mock_logger_error:
            mock_route_rec_query.side_effect = StorageNotFoundError("no record")

            await manager.store_update_results(TEST_CONN_ID, results)
            mock_logger_error.assert_called_once()

        with async_mock.patch.object(
            RouteRecord, "query", async_mock.CoroutineMock()
        ) as mock_route_rec_query, async_mock.patch.object(
            test_module.LOGGER, "error", async_mock.MagicMock()
        ) as mock_logger_error:
            mock_route_rec_query.return_value = [
                async_mock.MagicMock(delete_record=async_mock.CoroutineMock())
            ] * 2

            await manager.store_update_results(TEST_CONN_ID, results)
            mock_logger_error.assert_called_once()

    async def test_store_update_results_exists_relay(self, session, manager):
        """test_store_update_results_record_exists_relay."""
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            recipient_key=TEST_VERKEY,
            wallet_id="test_wallet",
        ).save(session)
        results = [
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_ADD,
                result=KeylistUpdated.RESULT_SUCCESS,
            )
        ]
        await manager.store_update_results(TEST_CONN_ID, results)
        routes = await RouteRecord.query(session)

        assert len(routes) == 1
        route = routes[0]
        assert route.recipient_key == TEST_VERKEY
        assert route.wallet_id == "test_wallet"
        assert route.connection_id == TEST_CONN_ID

    async def test_store_update_results_errors(self, caplog, manager):
        """test_store_update_results with errors."""
        caplog.set_level(logging.WARNING)
        results = [
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_ADD,
                result=KeylistUpdated.RESULT_NO_CHANGE,
            ),
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_REMOVE,
                result=KeylistUpdated.RESULT_SERVER_ERROR,
            ),
            KeylistUpdated(
                recipient_key=TEST_VERKEY,
                action=KeylistUpdateRule.RULE_REMOVE,
                result=KeylistUpdated.RESULT_CLIENT_ERROR,
            ),
        ]
        await manager.store_update_results(TEST_CONN_ID, results)
        assert "no_change" in caplog.text
        assert "client_error" in caplog.text
        assert "server_error" in caplog.text
        print(caplog.text)

    async def test_get_my_keylist(self, session, manager):
        """test_get_my_keylist."""
        await RouteRecord(
            role=RouteRecord.ROLE_CLIENT,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_VERKEY,
        ).save(session)
        # Non-client record to verify filtering
        await RouteRecord(
            role=RouteRecord.ROLE_SERVER,
            connection_id=TEST_CONN_ID,
            recipient_key=TEST_ROUTE_VERKEY,
        ).save(session)
        keylist = await manager.get_my_keylist(TEST_CONN_ID)
        assert keylist
        assert len(keylist) == 1
        assert keylist[0].connection_id == TEST_CONN_ID
        assert keylist[0].recipient_key == TEST_VERKEY
        assert keylist[0].role == RouteRecord.ROLE_CLIENT
