"""Test mediate grant message handler."""

import pytest
from aries_cloudagent.tests import mock

from aries_cloudagent.core.profile import ProfileSession

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......multitenant.base import BaseMultitenantManager

from ...messages.mediate_grant import MediationGrant
from ...models.mediation_record import MediationRecord
from ...manager import MediationManager

from ..mediation_grant_handler import MediationGrantHandler
from .. import mediation_grant_handler as test_module

TEST_CONN_ID = "conn-id"
TEST_BASE58_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_VERKEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_ENDPOINT = "https://example.com"


@pytest.fixture()
async def context():
    context = RequestContext.test_context()
    context.message = MediationGrant(endpoint=TEST_ENDPOINT, routing_keys=[TEST_VERKEY])
    context.connection_ready = True
    context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)
    yield context


@pytest.fixture()
async def session(context: RequestContext):
    yield await context.session()


@pytest.mark.asyncio
class TestMediationGrantHandler:
    """Test mediate grant message handler."""

    async def test_handler_no_active_connection(self, context: RequestContext):
        handler, responder = MediationGrantHandler(), MockResponder()
        context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(context, responder)
            assert "no active connection" in str(exc.value)

    async def test_handler_no_mediation_record(self, context: RequestContext):
        handler, responder = MediationGrantHandler(), MockResponder()
        with pytest.raises(HandlerException) as exc:
            await handler.handle(context, responder)
            assert "has not been requested" in str(exc.value)

    @pytest.mark.parametrize(
        "grant",
        [
            MediationGrant(endpoint=TEST_ENDPOINT, routing_keys=[TEST_VERKEY]),
            MediationGrant(endpoint=TEST_ENDPOINT, routing_keys=[TEST_BASE58_VERKEY]),
        ],
    )
    async def test_handler(
        self, grant: MediationGrant, session: ProfileSession, context: RequestContext
    ):
        handler, responder = MediationGrantHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(session)
        context.message = grant
        await handler.handle(context, responder)
        record = await MediationRecord.retrieve_by_connection_id(session, TEST_CONN_ID)
        assert record
        assert record.state == MediationRecord.STATE_GRANTED
        assert record.endpoint == TEST_ENDPOINT
        assert record.routing_keys == [TEST_VERKEY]

    async def test_handler_connection_has_set_to_default_meta(
        self, session: ProfileSession, context: RequestContext
    ):
        handler, responder = MediationGrantHandler(), MockResponder()
        record = MediationRecord(connection_id=TEST_CONN_ID)
        await record.save(session)
        with mock.patch.object(
            context.connection_record,
            "metadata_get",
            mock.CoroutineMock(return_value=True),
        ), mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_mediation_manager:
            await handler.handle(context, responder)
            mock_mediation_manager.return_value.set_default_mediator.assert_called_once_with(
                record
            )

    async def test_handler_multitenant_base_mediation(
        self, session: ProfileSession, context: RequestContext
    ):
        handler, responder = MediationGrantHandler(), mock.CoroutineMock()
        responder.send = mock.CoroutineMock()
        profile = context.profile

        profile.context.update_settings(
            {"multitenant.enabled": True, "wallet.id": "test_wallet"}
        )

        multitenant_mgr = mock.CoroutineMock()
        profile.context.injector.bind_instance(BaseMultitenantManager, multitenant_mgr)

        default_base_mediator = MediationRecord(routing_keys=["key1", "key2"])
        multitenant_mgr.get_default_mediator = mock.CoroutineMock()
        multitenant_mgr.get_default_mediator.return_value = default_base_mediator

        record = MediationRecord(connection_id=TEST_CONN_ID)
        await record.save(session)
        with mock.patch.object(MediationManager, "add_key") as add_key:
            keylist_updates = mock.MagicMock()
            add_key.return_value = keylist_updates

            await handler.handle(context, responder)

            add_key.assert_called_once_with("key2")
            responder.send.assert_called_once_with(
                keylist_updates, connection_id=TEST_CONN_ID
            )

    async def test_handler_connection_no_set_to_default(
        self, session: ProfileSession, context: RequestContext
    ):
        handler, responder = MediationGrantHandler(), MockResponder()
        record = MediationRecord(connection_id=TEST_CONN_ID)
        await record.save(session)
        with mock.patch.object(
            context.connection_record,
            "metadata_get",
            mock.CoroutineMock(return_value=False),
        ), mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_mediation_manager:
            await handler.handle(context, responder)
            mock_mediation_manager.return_value.set_default_mediator.assert_not_called()
