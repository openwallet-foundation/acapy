import asyncio
import json

import pytest
from aiohttp.test_utils import AioHTTPTestCase, unused_port

from ....core.profile import Profile
from ....tests import mock
from ....utils.testing import create_test_profile
from ...outbound.message import OutboundMessage
from ...wire_format import JsonWireFormat
from .. import http as test_module
from ..http import HttpTransport
from ..message import InboundMessage
from ..session import InboundSession


class TestHttpTransport(AioHTTPTestCase):
    async def asyncSetUp(self):
        self.message_results = []
        self.port = unused_port()
        self.profile = await create_test_profile()
        self.session = None
        self.transport = HttpTransport(
            "0.0.0.0", self.port, self.create_session, max_message_size=65535
        )
        self.transport.wire_format = JsonWireFormat()
        assert not self.transport.wire_format.get_recipient_keys(None)  # cover method
        self.result_event = None
        self.response_message = None
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

    def receive_message(
        self,
        profile: Profile,
        message: InboundMessage,
        can_respond: bool = False,
    ):
        message.wait_processing_complete = mock.CoroutineMock()
        self.message_results.append((message.payload, message.receipt, can_respond))
        if self.result_event:
            self.result_event.set()
        if self.response_message and self.session:
            self.session.set_response(self.response_message)

    def get_application(self):
        return self.transport.make_application()

    async def test_start_x(self):
        with mock.patch.object(test_module.web, "TCPSite", mock.MagicMock()) as mock_site:
            mock_site.return_value = mock.MagicMock(
                start=mock.CoroutineMock(side_effect=OSError())
            )
            with pytest.raises(test_module.InboundTransportSetupError):
                await self.transport.start()

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

    async def test_send_receive_message(self):
        await self.transport.start()

        test_message = {"~transport": {"return_route": "all"}, "test": "message"}
        test_response = {"response": "ok"}
        self.response_message = OutboundMessage(
            payload=None, enc_payload=json.dumps(test_response)
        )

        async with self.client.post("/", json=test_message) as resp:
            assert await resp.json() == {"response": "ok"}
            # Assert that Server header is cleared
            assert resp.headers.get("Server") is None

        await self.transport.stop()

    async def test_send_message_outliers(self):
        await self.transport.start()

        test_message = {"test": "message"}
        with mock.patch.object(
            test_module.HttpTransport, "create_session", mock.CoroutineMock()
        ) as mock_session:
            mock_session.return_value = mock.MagicMock(
                receive=mock.CoroutineMock(
                    return_value=mock.MagicMock(
                        receipt=mock.MagicMock(direct_response_requested=True),
                        wait_processing_complete=mock.CoroutineMock(),
                    )
                ),
                can_respond=True,
                profile=(await create_test_profile()),
                clear_response=mock.MagicMock(),
                wait_response=mock.CoroutineMock(return_value=b"Hello world"),
                response_buffer="something",
            )
            async with self.client.post("/", data=test_message) as resp:
                result = await resp.text()
            assert result == "Hello world"

            mock_session.return_value = mock.MagicMock(
                receive=mock.CoroutineMock(
                    side_effect=test_module.WireFormatParseError()
                ),
                profile=(await create_test_profile()),
            )
            async with self.client.post("/", data=test_message) as resp:
                status = resp.status
                result = await resp.text()
            assert status == 400
            assert str(status) in result

        await self.transport.stop()

    async def test_invite_message_handler(self):
        await self.transport.start()

        request = mock.MagicMock(query={"c_i": "dummy"})
        resp = await self.transport.invite_message_handler(request)
        assert b"You have received a connection invitation" in resp.body
        assert resp.status == 200

        request = mock.MagicMock(query={})
        resp = await self.transport.invite_message_handler(request)
        assert resp.body is None
        assert resp.status == 200

        await self.transport.stop()
