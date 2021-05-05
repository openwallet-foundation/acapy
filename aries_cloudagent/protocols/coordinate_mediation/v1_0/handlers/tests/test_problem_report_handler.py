"""Test Problem Report Handler."""
import pytest

from asynctest import mock as async_mock

from ......connections.models import connection_target
from ......connections.models.conn_record import ConnRecord
from ......connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ......core.profile import ProfileSession
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......storage.base import BaseStorage
from ......storage.error import StorageNotFoundError
from ......transport.inbound.receipt import MessageReceipt

from ...handlers import problem_report_handler as test_module
from ...manager import MediationManagerError, MediationManager
from ...messages.problem_report import CMProblemReport, ProblemReportReason


@pytest.fixture()
async def request_context() -> RequestContext:
    ctx = RequestContext.test_context()
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest.fixture()
async def connection_record(request_context, session) -> ConnRecord:
    record = ConnRecord()
    request_context.connection_record = record
    await record.save(session)
    yield record


@pytest.fixture()
async def session(request_context) -> ProfileSession:
    yield await request_context.session()


class TestCMProblemReportHandler:
    @pytest.mark.asyncio
    async def test_cover(self, request_context, connection_record):
        request_context.message = CMProblemReport(
            description={
                "en": "Mediation not granted",
                "code": ProblemReportReason.MEDIATION_NOT_GRANTED.value,
            }
        )
        handler = test_module.CMProblemReportHandler()
        responder = MockResponder()
        await handler.handle(context=request_context, responder=responder)
