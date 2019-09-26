import asyncio
from io import StringIO
from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import conductor as test_module
from ..admin.base_server import BaseAdminServer
from ..config.base_context import ContextBuilder
from ..config.injection_context import InjectionContext
from ..messaging.connections.manager import ConnectionManager
from ..messaging.connections.models.connection_record import ConnectionRecord
from ..messaging.connections.models.connection_target import ConnectionTarget
from ..messaging.message_delivery import MessageDelivery
from ..messaging.serializer import MessageSerializer
from ..messaging.outbound_message import OutboundMessage
from ..messaging.protocol_registry import ProtocolRegistry
from ..stats import Collector
from ..storage.base import BaseStorage
from ..storage.basic import BasicStorage
from ..transport.inbound.base import InboundTransportConfiguration
from ..transport.outbound.queue.base import BaseOutboundMessageQueue
from ..transport.outbound.queue.basic import BasicOutboundMessageQueue
from ..wallet.base import BaseWallet
from ..wallet.basic import BasicWallet


class Config:
    good_inbound_transports = {"transport.inbound_configs": [["http", "host", 80]]}
    good_outbound_transports = {"transport.outbound_configs": ["http"]}
    bad_inbound_transports = {"transport.inbound_configs": [["bad", "host", 80]]}
    bad_outbound_transports = {"transport.outbound_configs": ["bad"]}
    test_settings = {}


class StubContextBuilder(ContextBuilder):
    def __init__(self, settings):
        super().__init__(settings)
        self.message_serializer = async_mock.create_autospec(MessageSerializer())

    async def build(self) -> InjectionContext:
        context = InjectionContext(settings=self.settings)
        context.injector.enforce_typing = False
        context.injector.bind_instance(
            BaseOutboundMessageQueue, BasicOutboundMessageQueue()
        )
        context.injector.bind_instance(BaseStorage, BasicStorage())
        context.injector.bind_instance(BaseWallet, BasicWallet())
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(MessageSerializer, self.message_serializer)
        return context


class StubCollectorContextBuilder(StubContextBuilder):
    async def build(self) -> InjectionContext:
        context = await super().build()
        context.injector.bind_instance(Collector, Collector())
        return context


class TestConductor(AsyncTestCase, Config):
    async def test_startup(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(self.good_inbound_transports)
        builder.update_settings(self.good_outbound_transports)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger:

            await conductor.setup()

            mock_inbound_mgr.return_value.register.assert_called_once_with(
                InboundTransportConfiguration(module="http", host="host", port=80),
                conductor.inbound_message_router,
                conductor.register_socket,
            )
            mock_outbound_mgr.return_value.register.assert_called_once_with("http")

            mock_inbound_mgr.return_value.registered_transports = []
            mock_outbound_mgr.return_value.registered_transports = []

            await conductor.start()

            mock_inbound_mgr.return_value.start.assert_awaited_once_with()
            mock_outbound_mgr.return_value.start.assert_awaited_once_with()

            await conductor.stop()

            mock_inbound_mgr.return_value.stop.assert_awaited_once_with()
            mock_outbound_mgr.return_value.stop.assert_awaited_once_with()

    async def test_inbound_message_handler(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        await conductor.setup()

        with async_mock.patch.object(
            conductor.dispatcher, "dispatch", autospec=True
        ) as mock_dispatch:
            dispatch_result = """{"@type": "..."}"""
            mock_dispatch.return_value.return_value = asyncio.Future()
            mock_dispatch.return_value.return_value.set_result(None)

            delivery = MessageDelivery()
            parsed_msg = {}
            mock_serializer = builder.message_serializer
            mock_serializer.extract_message_type.return_value = "message_type"
            mock_serializer.parse_message.return_value = (parsed_msg, delivery)

            message_body = "{}"
            transport = "http"
            complete = await conductor.inbound_message_router(message_body, transport)
            asyncio.wait_for(complete, 1.0)

            mock_serializer.parse_message.assert_awaited_once_with(
                conductor.context, message_body, transport
            )

            mock_dispatch.assert_awaited_once_with(
                parsed_msg, delivery, None, conductor.outbound_message_router
            )

    async def test_direct_response(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        await conductor.setup()

        single_response = asyncio.Future()
        dispatch_result = """{"@type": "..."}"""

        async def mock_dispatch(parsed_msg, delivery, connection, outbound):
            socket_id = delivery.socket_id
            socket = conductor.sockets[socket_id]
            socket.reply_mode = "all"
            reply = OutboundMessage(
                dispatch_result,
                connection_id=None,
                encoded=False,
                endpoint=None,
                reply_socket_id=socket_id,
            )
            await outbound(reply)
            result = asyncio.Future()
            result.set_result(None)
            return result

        with async_mock.patch.object(conductor.dispatcher, "dispatch", mock_dispatch):

            delivery = MessageDelivery()
            parsed_msg = {}
            mock_serializer = builder.message_serializer
            mock_serializer.extract_message_type.return_value = "message_type"
            mock_serializer.parse_message.return_value = (parsed_msg, delivery)

            message_body = "{}"
            transport = "http"
            complete = await conductor.inbound_message_router(
                message_body, transport, None, single_response
            )
            asyncio.wait_for(complete, 1.0)

            assert single_response.result() == dispatch_result

    async def test_outbound_message_handler(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:

            await conductor.setup()

            payload = "{}"
            target = ConnectionTarget(
                endpoint="endpoint", recipient_keys=(), routing_keys=(), sender_key=""
            )
            message = OutboundMessage(payload=payload, target=target)

            await conductor.outbound_message_router(message)

            mock_serializer = builder.message_serializer
            mock_serializer.encode_message.assert_awaited_once_with(
                conductor.context,
                payload,
                target.recipient_keys,
                target.routing_keys,
                target.sender_key,
            )

            mock_outbound_mgr.return_value.send_message.assert_awaited_once_with(
                message
            )

    async def test_connection_target(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        await conductor.setup()

        test_target = ConnectionTarget(
            endpoint="endpoint", recipient_keys=(), routing_keys=(), sender_key=""
        )
        test_conn_id = "1"

        with async_mock.patch.object(
            ConnectionRecord, "retrieve_by_id", autospec=True
        ) as retrieve_by_id, async_mock.patch.object(
            ConnectionManager, "get_connection_target", autospec=True
        ) as get_target:

            get_target.return_value = test_target

            target = await conductor.get_connection_target(test_conn_id)

            assert target is test_target

    async def test_admin(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"admin.enabled": "1"})
        conductor = test_module.Conductor(builder)

        await conductor.setup()
        admin = await conductor.context.inject(BaseAdminServer)
        assert admin is conductor.admin_server

        with async_mock.patch.object(
            admin, "start", autospec=True
        ) as admin_start, async_mock.patch.object(
            admin, "stop", autospec=True
        ) as admin_stop:
            await conductor.start()
            admin_start.assert_awaited_once_with()

            await conductor.stop()
            admin_stop.assert_awaited_once_with()

    async def test_setup_collector(self):
        builder: ContextBuilder = StubCollectorContextBuilder(self.test_settings)
        builder.update_settings(self.good_inbound_transports)
        builder.update_settings(self.good_outbound_transports)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger:

            await conductor.setup()

    async def test_print_invite(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(
            {"debug.print_invitation": True, "invite_base_url": "http://localhost"}
        )
        conductor = test_module.Conductor(builder)

        with mock.patch("sys.stdout", new=StringIO()) as captured:
            await conductor.setup()

            await conductor.start()

            await conductor.stop()

            assert "http://localhost?c_i=" in captured.getvalue()
