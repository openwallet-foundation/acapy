"""Test mediate grant message handler."""
import pytest
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import mediation_grant_handler as test_module

from ......connections.models.conn_record import ConnRecord
from ......messaging.base_handler import HandlerException
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ...messages.mediate_grant import MediationGrant
from ...models.mediation_record import MediationRecord
from ..mediation_grant_handler import MediationGrantHandler

TEST_CONN_ID = "conn-id"
TEST_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_ENDPOINT = "https://example.com"


class TestMediationGrantHandler(AsyncTestCase):
    """Test mediate grant message handler."""

    async def setUp(self):
        """Setup test dependencies."""
        self.context = RequestContext.test_context()
        self.session = await self.context.session()
        self.context.message = MediationGrant(
            endpoint=TEST_ENDPOINT, routing_keys=[TEST_VERKEY]
        )
        self.context.connection_ready = True
        self.context.connection_record = ConnRecord(connection_id=TEST_CONN_ID)

    async def test_handler_no_active_connection(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        self.context.connection_ready = False
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "no active connection" in str(exc.value)

    async def test_handler_no_mediation_record(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        with pytest.raises(HandlerException) as exc:
            await handler.handle(self.context, responder)
            assert "has not been requested" in str(exc.value)

    async def test_handler(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        await MediationRecord(connection_id=TEST_CONN_ID).save(self.session)
        await handler.handle(self.context, responder)
        record = await MediationRecord.retrieve_by_connection_id(
            self.session, TEST_CONN_ID
        )
        assert record
        assert record.state == MediationRecord.STATE_GRANTED
        assert record.endpoint == TEST_ENDPOINT
        assert record.routing_keys == [TEST_VERKEY]

    async def test_handler_connection_has_set_to_default_meta(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        record = MediationRecord(connection_id=TEST_CONN_ID)
        await record.save(self.session)
        with async_mock.patch.object(
            self.context.connection_record,
            "metadata_get",
            async_mock.CoroutineMock(return_value=True),
        ), async_mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_mediation_manager:
            await handler.handle(self.context, responder)
            mock_mediation_manager.return_value.set_default_mediator.assert_called_once_with(
                record
            )

    async def test_handler_connection_no_set_to_default(self):
        handler, responder = MediationGrantHandler(), MockResponder()
        record = MediationRecord(connection_id=TEST_CONN_ID)
        await record.save(self.session)
        with async_mock.patch.object(
            self.context.connection_record,
            "metadata_get",
            async_mock.CoroutineMock(return_value=False),
        ), async_mock.patch.object(
            test_module, "MediationManager", autospec=True
        ) as mock_mediation_manager:
            await handler.handle(self.context, responder)
            mock_mediation_manager.return_value.set_default_mediator.assert_not_called()
