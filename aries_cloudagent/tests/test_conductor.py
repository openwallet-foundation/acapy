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
from ..transport.outbound.base import OutboundDeliveryError
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
            assert mock_dispatch.call_args[0][2] is None  # admin webhook router
            assert callable(mock_dispatch.call_args[0][3])

    async def test_outbound_message_handler_return_route(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        test_to_verkey = "test-to-verkey"
        test_from_verkey = "test-from-verkey"

        await conductor.setup()

        payload = "{}"
        message = OutboundMessage(payload=payload)
        message.reply_to_verkey = test_to_verkey
        receipt = MessageReceipt()
        receipt.recipient_verkey = test_from_verkey
        inbound = InboundMessage("[]", receipt)

        with async_mock.patch.object(
            conductor.inbound_transport_manager, "return_to_session"
        ) as mock_return, async_mock.patch.object(
            conductor, "queue_outbound", async_mock.CoroutineMock()
        ) as mock_queue:
            mock_return.return_value = True
            await conductor.outbound_message_router(conductor.context, message)
            mock_return.assert_called_once_with(message)
            mock_queue.assert_not_awaited()

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

    async def test_start_static(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(test_module, "ConnectionManager") as mock_mgr:
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = async_mock.CoroutineMock()
            await conductor.start()
            mock_mgr.return_value.create_static_connection.assert_awaited_once()

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

    async def test_webhook_router(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(
            {"debug.print_invitation": True, "invite_base_url": "http://localhost"}
        )
        conductor = test_module.Conductor(builder)

        test_topic = "test-topic"
        test_payload = {"test": "payload"}
        test_endpoint = "http://example"
        test_retries = 2

        await conductor.setup()
        with async_mock.patch.object(
            conductor.outbound_transport_manager, "enqueue_webhook"
        ) as mock_enqueue:
            conductor.webhook_router(
                test_topic, test_payload, test_endpoint, test_retries
            )
            mock_enqueue.assert_called_once_with(
                test_topic, test_payload, test_endpoint, test_retries
            )

        # swallow error
        with async_mock.patch.object(
            conductor.outbound_transport_manager,
            "enqueue_webhook",
            side_effect=OutboundDeliveryError,
        ) as mock_enqueue:
            conductor.webhook_router(
                test_topic, test_payload, test_endpoint, test_retries
            )
            mock_enqueue.assert_called_once_with(
                test_topic, test_payload, test_endpoint, test_retries
            )

