import asyncio
import json

from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop, unused_port
from aiohttp import web
from asynctest import mock as async_mock

from ...outbound.message import OutboundMessage
from ...wire_format import JsonWireFormat

from ..http import HttpTransport
from ..message import InboundMessage
from ..session import InboundSession


class TestHttpTransport(AioHTTPTestCase):
    def setUp(self):
        self.message_results = []
        self.port = unused_port()
        self.session = None
        self.transport = HttpTransport("0.0.0.0", self.port, self.create_session)
        self.transport.wire_format = JsonWireFormat()
        self.result_event = None
        self.response_message = None
        super(TestHttpTransport, self).setUp()

    def create_session(
        self,
        transport_type,
        *,
        client_info,
        wire_format,
        can_respond: bool = False,
        **kwargs
    ):
        if not self.session:
            session = InboundSession(
                context=None,
                can_respond=can_respond,
                inbound_handler=self.receive_message,
                session_id=None,
                wire_format=wire_format,
                client_info=client_info,
                transport_type=transport_type,
            )
            self.session = session
        result = asyncio.Future()
        result.set_result(self.session)
        return result

    def receive_message(self, message: InboundMessage, can_respond: bool = False):
        self.message_results.append((message.payload, message.receipt, can_respond))
        if self.result_event:
            self.result_event.set()
        if self.response_message and self.session:
            self.session.set_response(self.response_message)

    def get_application(self):
        return self.transport.make_application()

    @unittest_run_loop
    async def test_send_message(self):
        await self.transport.start()

        test_message = {"test": "message"}
        async with self.client.post("/", json=test_message) as resp:
            await resp.text()

        assert self.session is not None
        assert self.session.transport_type == "http"
        assert len(self.message_results) == 1
        assert self.message_results[0][0] == test_message

        await self.transport.stop()

    @unittest_run_loop
    async def test_send_receive_message(self):
        await self.transport.start()

        test_message = {"~transport": {"return_route": "all"}, "test": "message"}
        test_response = {"response": "ok"}
        self.response_message = OutboundMessage(
            payload=None, enc_payload=json.dumps(test_response)
        )

        async with self.client.post("/", json=test_message) as resp:
            assert await resp.json() == {"response": "ok"}

        await self.transport.stop()
