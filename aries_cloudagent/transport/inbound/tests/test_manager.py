import asyncio

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ....core.in_memory import InMemoryProfile

from ...outbound.message import OutboundMessage

from ...wire_format import BaseWireFormat
from ..base import InboundTransportConfiguration, InboundTransportRegistrationError
from ..manager import InboundTransportManager


class TestInboundTransportManager(AsyncTestCase):
    def setUp(self):
        self.profile = InMemoryProfile.test_profile()

    def test_register_path(self):
        mgr = InboundTransportManager(self.profile, None)

        config = InboundTransportConfiguration(module="http", host="0.0.0.0", port=80)
        mgr.register(config)

        config = InboundTransportConfiguration(
            module="no_such_package.http", host="0.0.0.0", port=80
        )
        with self.assertRaises(InboundTransportRegistrationError):
            mgr.register(config)

        config = InboundTransportConfiguration(
            module="notransport", host="0.0.0.0", port=80
        )
        with self.assertRaises(InboundTransportRegistrationError):
            mgr.register(config)

    async def test_setup(self):
        test_module = "http"
        test_host = "host"
        test_port = 80
        self.profile.context.update_settings(
            {
                "transport.max_message_size": 65535,
                "transport.inbound_configs": [[test_module, test_host, test_port]],
                "transport.enable_undelivered_queue": True,
            }
        )
        mgr = InboundTransportManager(self.profile, None)

        with async_mock.patch.object(mgr, "register") as mock_register:
            await mgr.setup()
            mock_register.assert_called_once()
            tcfg: InboundTransportConfiguration = mock_register.call_args[0][0]
            assert (tcfg.module, tcfg.host, tcfg.port) == (
                test_module,
                test_host,
                test_port,
            )

        assert mgr.undelivered_queue

    async def test_start_stop(self):
        transport = async_mock.MagicMock()
        transport.start = async_mock.CoroutineMock()
        transport.stop = async_mock.CoroutineMock()

        mgr = InboundTransportManager(self.profile, None)
        mgr.register_transport(transport, "transport_cls")
        await mgr.start()
        await mgr.task_queue
        transport.start.assert_awaited_once_with()
        assert mgr.get_transport_instance("transport_cls") is transport

        await mgr.stop()
        transport.stop.assert_awaited_once_with()

    async def test_create_session(self):
        test_wire_format = async_mock.MagicMock()
        self.profile.context.injector.bind_instance(BaseWireFormat, test_wire_format)

        test_inbound_handler = async_mock.CoroutineMock()
        mgr = InboundTransportManager(self.profile, test_inbound_handler)
        test_transport = "http"
        test_accept = True
        test_can_respond = True
        test_client_info = {"client": "info"}
        session = await mgr.create_session(
            test_transport,
            accept_undelivered=test_accept,
            can_respond=test_can_respond,
            client_info=test_client_info,
        )

        assert session.accept_undelivered == test_accept
        assert session.can_respond == test_can_respond
        assert session.client_info == test_client_info
        assert session.transport_type == test_transport
        assert session.wire_format is test_wire_format
        assert session.session_id and mgr.sessions[session.session_id] is session

        await session.inbound_handler()
        test_inbound_handler.assert_awaited_once_with()

        session.close_handler(session)
        assert session.session_id not in mgr.sessions

    async def test_return_to_session(self):
        mgr = InboundTransportManager(self.profile, None)
        test_wire_format = async_mock.MagicMock()

        session = await mgr.create_session("http", wire_format=test_wire_format)

        test_outbound = OutboundMessage(payload=None)
        test_outbound.reply_session_id = session.session_id

        with async_mock.patch.object(
            session, "accept_response", return_value=True
        ) as mock_accept:
            assert mgr.return_to_session(test_outbound) is True
            mock_accept.assert_called_once_with(test_outbound)

        test_outbound = OutboundMessage(payload=None)
        test_outbound.reply_session_id = None

        with async_mock.patch.object(
            session, "accept_response", return_value=False
        ) as mock_accept:
            assert mgr.return_to_session(test_outbound) is False
            mock_accept.assert_called_once_with(test_outbound)

        with async_mock.patch.object(
            session, "accept_response", return_value=True
        ) as mock_accept:
            assert mgr.return_to_session(test_outbound) is True
            mock_accept.assert_called_once_with(test_outbound)

    async def test_close_return(self):
        test_return = async_mock.MagicMock()
        mgr = InboundTransportManager(self.profile, None, return_inbound=test_return)
        test_wire_format = async_mock.MagicMock()

        session = await mgr.create_session("http", wire_format=test_wire_format)

        test_outbound = OutboundMessage(payload=None)
        session.set_response(test_outbound)

        session.close()
        test_return.assert_called_once_with(session.profile, test_outbound)

    async def test_dispatch_complete_undelivered(self):
        mgr = InboundTransportManager(self.profile, None)
        test_wire_format = async_mock.MagicMock(
            parse_message=async_mock.CoroutineMock(return_value=("payload", "receipt"))
        )
        session = await mgr.create_session(
            "http", wire_format=test_wire_format, accept_undelivered=True
        )
        inbound_msg = await session.parse_inbound("payload")
        mgr.dispatch_complete(inbound_msg, None)

    async def test_close_x(self):
        mgr = InboundTransportManager(self.profile, None)
        mock_session = async_mock.MagicMock(response_buffer=async_mock.MagicMock())
        mgr.closed_session(mock_session)

    async def test_process_undelivered(self):
        self.profile.context.update_settings(
            {"transport.enable_undelivered_queue": True}
        )
        test_verkey = "test-verkey"
        test_wire_format = async_mock.MagicMock()
        mgr = InboundTransportManager(self.profile, None)
        await mgr.setup()

        test_outbound = OutboundMessage(payload=None)
        test_outbound.reply_to_verkey = test_verkey
        assert mgr.return_undelivered(test_outbound)
        assert mgr.undelivered_queue.has_message_for_key(test_verkey)

        session = await mgr.create_session(
            "http", can_respond=True, wire_format=test_wire_format
        )
        session.add_reply_verkeys(test_verkey)

        with async_mock.patch.object(
            session, "accept_response", return_value=True
        ) as mock_accept:
            mgr.process_undelivered(session)
            mock_accept.assert_called_once_with(test_outbound)
        assert not mgr.undelivered_queue.has_message_for_key(test_verkey)

    async def test_return_undelivered_false(self):
        self.profile.context.update_settings(
            {"transport.enable_undelivered_queue": False}
        )
        test_verkey = "test-verkey"
        test_wire_format = async_mock.MagicMock()
        mgr = InboundTransportManager(self.profile, None)
        await mgr.setup()

        test_outbound = OutboundMessage(payload=None)
        test_outbound.reply_to_verkey = test_verkey
        assert not mgr.return_undelivered(test_outbound)
