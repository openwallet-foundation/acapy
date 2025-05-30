import asyncio
import json

import pytest
from aiohttp.test_utils import AioHTTPTestCase, unused_port

from ....config.injection_context import InjectionContext
from ....tests import mock
from ....utils.testing import create_test_profile
from ...outbound.message import OutboundMessage
from ...wire_format import JsonWireFormat
from .. import ws as test_module
from ..message import InboundMessage
from ..session import InboundSession
from ..ws import WsTransport


class TestWsTransport(AioHTTPTestCase):
    async def asyncSetUp(self):
        self.message_results = []
        self.port = unused_port()
        self.session = None
        self.profile = await create_test_profile()
        self.transport = WsTransport(
            "0.0.0.0", self.port, self.create_session, root_profile=self.profile
        )
        self.transport.wire_format = JsonWireFormat()
        self.result_event = None
        await super().asyncSetUp()

    def get_profile(self):
        return self.profile

    def create_session(
        self,
        transport_type,
        *,
        client_info,
        wire_format,
        can_respond: bool = False,
        **kwargs,
    ):
        if not self.session:
            session = InboundSession(
                profile=self.get_profile(),
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

    def get_application(self):
        return self.transport.make_application()

    def receive_message(
        self,
        context: InjectionContext,
        message: InboundMessage,
        can_respond: bool = False,
    ):
        self.message_results.append((message.payload, message.receipt, can_respond))
        if self.result_event:
            self.result_event.set()

    async def test_start_x(self):
        with mock.patch.object(test_module.web, "TCPSite", mock.MagicMock()) as mock_site:
            mock_site.return_value = mock.MagicMock(
                start=mock.CoroutineMock(side_effect=OSError())
            )
            with pytest.raises(test_module.InboundTransportSetupError):
                await self.transport.start()

    async def test_message_and_response(self):
        await self.transport.start()

        test_message = {"test": "message"}
        test_response = {"response": "ok"}

        async with self.client.ws_connect("/") as ws:
            self.result_event = asyncio.Event()
            await ws.send_json(test_message)
            await asyncio.wait_for(self.result_event.wait(), timeout=0.1)

            assert self.session is not None
            assert len(self.message_results) == 1
            received, _, can_respond = self.message_results[0]
            assert received == test_message
            assert can_respond

            response = OutboundMessage(
                payload=None, enc_payload=json.dumps(test_response)
            )
            self.session.set_response(response)

            result = await asyncio.wait_for(ws.receive_json(), 1.0)
            assert result == {"response": "ok"}

            # Check the Server header is removed
            assert "Server" not in ws._response.headers

        await self.transport.stop()
