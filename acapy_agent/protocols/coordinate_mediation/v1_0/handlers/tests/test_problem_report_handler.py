"""Test Problem Report Handler."""

import pytest
import pytest_asyncio

from ......connections.models.conn_record import ConnRecord
from ......messaging.request_context import RequestContext
from ......messaging.responder import MockResponder
from ......transport.inbound.receipt import MessageReceipt
from ......utils.testing import create_test_profile
from ...handlers import problem_report_handler as test_module
from ...messages.problem_report import CMProblemReport, ProblemReportReason


@pytest_asyncio.fixture
async def request_context():
    ctx = RequestContext.test_context(await create_test_profile())
    ctx.message_receipt = MessageReceipt()
    yield ctx


@pytest_asyncio.fixture
async def connection_record(request_context, session):
    record = ConnRecord()
    request_context.connection_record = record
    await record.save(session)
    yield record


@pytest_asyncio.fixture
async def session(request_context):
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
