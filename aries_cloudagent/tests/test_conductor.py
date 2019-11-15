import asyncio
from io import StringIO
from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import conductor as test_module
from ..admin.base_server import BaseAdminServer
from ..config.base_context import ContextBuilder
from ..config.injection_context import InjectionContext
from ..protocols.connections.manager import ConnectionManager
from ..connections.models.connection_record import ConnectionRecord
from ..connections.models.connection_target import ConnectionTarget
from ..connections.models.diddoc import (
    DIDDoc,
    PublicKey,
    PublicKeyType,
    Service,
)
from ..messaging.protocol_registry import ProtocolRegistry
from ..stats import Collector
from ..storage.base import BaseStorage
from ..storage.basic import BasicStorage
from ..transport.inbound.base import InboundTransportConfiguration
from ..transport.inbound.message import InboundMessage
from ..transport.inbound.receipt import MessageReceipt
from ..transport.outbound.message import OutboundMessage
from ..transport.wire_format import BaseWireFormat
from ..wallet.base import BaseWallet
from ..wallet.basic import BasicWallet


class Config:
    test_settings = {}
    test_settings_with_queue = {"queue.enable_undelivered_queue": True}


class TestDIDs:

    test_seed = "testseed000000000000000000000001"
    test_did = "55GkHamhTU1ZbTbV2ab9DE"
    test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
    test_endpoint = "http://localhost"

    test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
    test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

    def make_did_doc(self, did, verkey):
        doc = DIDDoc(did=did)
        controller = did
        ident = "1"
        pk_value = verkey
        pk = PublicKey(
            did, ident, pk_value, PublicKeyType.ED25519_SIG_2018, controller, False
        )
        doc.set(pk)
        recip_keys = [pk]
        router_keys = []
        service = Service(
            did, "indy", "IndyAgent", recip_keys, router_keys, self.test_endpoint
        )
        doc.set(service)
        return doc, pk


class StubContextBuilder(ContextBuilder):
    def __init__(self, settings):
        super().__init__(settings)
        self.wire_format = async_mock.create_autospec(BaseWireFormat())

    async def build(self) -> InjectionContext:
        context = InjectionContext(settings=self.settings)
        context.injector.enforce_typing = False
        context.injector.bind_instance(BaseStorage, BasicStorage())
        context.injector.bind_instance(BaseWallet, BasicWallet())
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(BaseWireFormat, self.wire_format)
        return context


class StubCollectorContextBuilder(StubContextBuilder):
    async def build(self) -> InjectionContext:
        context = await super().build()
        context.injector.bind_instance(Collector, Collector())
        return context


class TestConductor(AsyncTestCase, Config, TestDIDs):
    async def test_startup(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger:

            await conductor.setup()

            mock_inbound_mgr.return_value.setup.assert_awaited_once()
            mock_outbound_mgr.return_value.setup.assert_awaited_once()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}

            await conductor.start()

            mock_inbound_mgr.return_value.start.assert_awaited_once_with()
            mock_outbound_mgr.return_value.start.assert_awaited_once_with()

            mock_logger.print_banner.assert_called_once()

            await conductor.stop()

            mock_inbound_mgr.return_value.stop.assert_awaited_once_with()
            mock_outbound_mgr.return_value.stop.assert_awaited_once_with()

    async def test_inbound_message_handler(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        await conductor.setup()

        with async_mock.patch.object(
            conductor.dispatcher, "queue_message", autospec=True
        ) as mock_dispatch:

            message_body = "{}"
            receipt = MessageReceipt()
            message = InboundMessage(message_body, receipt)

            conductor.inbound_message_router(message)

            mock_dispatch.assert_called_once()
            assert mock_dispatch.call_args[0][0] is message
            assert mock_dispatch.call_args[0][1] == conductor.outbound_message_router
            assert callable(mock_dispatch.call_args[0][2])

    # async def test_direct_response(self):
    #     builder: ContextBuilder = StubContextBuilder(self.test_settings)
    #     conductor = test_module.Conductor(builder)

    #     await conductor.setup()

    #     single_response = asyncio.Future()
    #     dispatch_result = """{"@type": "..."}"""

    #     async def mock_dispatch(parsed_msg, delivery, connection, outbound):
    #         socket_id = delivery.socket_id
    #         socket = conductor.sockets[socket_id]
    #         socket.reply_mode = "all"
    #         reply = OutboundMessage(
    #             dispatch_result,
    #             connection_id=None,
    #             encoded=False,
    #             endpoint=None,
    #             reply_socket_id=socket_id,
    #         )
    #         await outbound(reply)
    #         result = asyncio.Future()
    #         result.set_result(None)
    #         return result

    #     with async_mock.patch.object(conductor.dispatcher, "dispatch", mock_dispatch):

    #         delivery = MessageReceipt()
    #         parsed_msg = {}
    #         mock_serializer = builder.message_serializer
    #         mock_serializer.extract_message_type.return_value = "message_type"
    #         mock_serializer.parse_message.return_value = (parsed_msg, delivery)

    #         message_body = "{}"
    #         transport = "http"
    #         complete = await conductor.inbound_message_router(
    #             message_body, transport, None, single_response
    #         )
    #         await asyncio.wait_for(complete, 1.0)

    #         assert single_response.result() == dispatch_result

    async def test_outbound_message_handler_with_target(self):
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

            await conductor.outbound_message_router(conductor.context, message)

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.context, message
            )

    async def test_outbound_message_handler_with_connection(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr:

            await conductor.setup()

            payload = "{}"
            connection_id = "connection_id"
            message = OutboundMessage(payload=payload, connection_id=connection_id)

            await conductor.outbound_message_router(conductor.context, message)

            conn_mgr.assert_called_once_with(conductor.context)
            conn_mgr.return_value.get_connection_targets.assert_awaited_once_with(
                connection_id=connection_id
            )
            assert (
                message.target_list
                is conn_mgr.return_value.get_connection_targets.return_value
            )

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.context, message
            )

    # async def test_outbound_queue_add_with_no_endpoint(self):
    #     builder: ContextBuilder = StubContextBuilder(self.test_settings_with_queue)
    #     conductor = test_module.Conductor(builder)
    #     # set up relationship without endpoint
    #     with async_mock.patch.object(
    #         test_module, "DeliveryQueue", autospec=True
    #     ) as mock_delivery_queue:

    #         await conductor.setup()

    #         sender_did_doc, sender_pk = self.make_did_doc(
    #             self.test_did, self.test_verkey
    #         )
    #         target_did_doc, target_pk = self.make_did_doc(
    #             self.test_target_did, self.test_target_verkey
    #         )

    #         payload = "{}"
    #         target = ConnectionTarget(
    #             recipient_keys=[target_pk], routing_keys=(), sender_key=sender_pk
    #         )
    #         message = OutboundMessage(payload=payload, target=target)

    #         await conductor.outbound_message_router(message)

    #         mock_delivery_queue.return_value.add_message.assert_called_once_with(
    #             message
    #         )

    # async def test_outbound_queue_check_on_inbound(self):
    #     builder: ContextBuilder = StubContextBuilder(self.test_settings_with_queue)
    #     conductor = test_module.Conductor(builder)

    #     with async_mock.patch.object(
    #         test_module, "DeliveryQueue", autospec=True
    #     ) as mock_delivery_queue:
    #         await conductor.setup()

    #         async def mock_dispatch(parsed_msg, delivery, connection, outbound):
    #             result = asyncio.Future()
    #             result.set_result(None)
    #             return result

    #         # set up relationship without endpoint
    #         with async_mock.patch.object(
    #             conductor.dispatcher, "dispatch", mock_dispatch
    #         ) as mock_dispatch_method, async_mock.patch.object(
    #             test_module, "ConnectionManager", autospec=True
    #         ) as mock_connection_manager:

    #             sender_did_doc, sender_pk = self.make_did_doc(
    #                 self.test_did, self.test_verkey
    #             )

    #             # we don't need the connection, so avoid looking for one.
    #             mock_connection_manager.find_message_connection.return_value = None

    #             delivery = MessageReceipt()
    #             delivery.sender_verkey = sender_pk
    #             delivery.direct_response_requested = "all"
    #             parsed_msg = {}
    #             mock_serializer = builder.message_serializer
    #             mock_serializer.extract_message_type.return_value = (
    #                 "message_type"  # messaging.trustping.message_types.PING
    #             )
    #             mock_serializer.parse_message.return_value = (parsed_msg, delivery)

    #             message_body = "{}"
    #             transport = "http"
    #             delivery_future = asyncio.Future()
    #             r_future = await conductor.inbound_message_router(
    #                 message_body, transport, single_response=delivery_future
    #             )
    #             r_future_result = await r_future  # required for test passing.
    #             mock_delivery_queue.return_value.has_message_for_key.assert_called_once_with(
    #                 sender_pk.value
    #             )

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

        with async_mock.patch("sys.stdout", new=StringIO()) as captured:
            await conductor.setup()

            await conductor.start()

            await conductor.stop()

            assert "http://localhost?c_i=" in captured.getvalue()
