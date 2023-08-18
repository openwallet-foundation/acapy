from io import StringIO

import mock as async_mock
from unittest import IsolatedAsyncioTestCase

from ...admin.base_server import BaseAdminServer
from ...config.base_context import ContextBuilder
from ...config.injection_context import InjectionContext
from ...connections.models.conn_record import ConnRecord
from ...connections.models.connection_target import ConnectionTarget
from ...connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ...core.event_bus import EventBus, MockEventBus
from ...core.in_memory import InMemoryProfileManager
from ...core.profile import ProfileManager
from ...core.protocol_registry import ProtocolRegistry
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...protocols.coordinate_mediation.mediation_invite_store import (
    MediationInviteRecord,
)
from ...protocols.coordinate_mediation.v1_0.models.mediation_record import (
    MediationRecord,
)
from ...protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ...resolver.did_resolver import DIDResolver
from ...storage.base import BaseStorage
from ...storage.error import StorageNotFoundError
from ...transport.inbound.message import InboundMessage
from ...transport.inbound.receipt import MessageReceipt
from ...transport.outbound.base import OutboundDeliveryError
from ...transport.outbound.manager import QueuedOutboundMessage
from ...transport.outbound.message import OutboundMessage
from ...transport.outbound.status import OutboundSendStatus
from ...transport.pack_format import PackWireFormat
from ...transport.wire_format import BaseWireFormat
from ...utils.stats import Collector
from ...version import __version__
from ...wallet.base import BaseWallet
from ...wallet.did_method import SOV, DIDMethods
from ...wallet.key_type import ED25519
from .. import conductor as test_module


class Config:
    test_settings = {"admin.webhook_urls": ["http://sample.webhook.ca"]}
    test_settings_admin = {
        "admin.webhook_urls": ["http://sample.webhook.ca"],
        "admin.enabled": True,
    }
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
        self.wire_format = async_mock.create_autospec(PackWireFormat())

    async def build_context(self) -> InjectionContext:
        context = InjectionContext(settings=self.settings, enforce_typing=False)
        context.injector.bind_instance(ProfileManager, InMemoryProfileManager())
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(BaseWireFormat, self.wire_format)
        context.injector.bind_instance(DIDMethods, DIDMethods())
        context.injector.bind_instance(DIDResolver, DIDResolver([]))
        context.injector.bind_instance(EventBus, MockEventBus())
        return context


class StubCollectorContextBuilder(StubContextBuilder):
    async def build_context(self) -> InjectionContext:
        context = await super().build_context()
        context.injector.bind_instance(Collector, Collector())
        return context


class TestConductor(IsolatedAsyncioTestCase, Config, TestDIDs):
    async def test_startup_version_record_exists(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(return_value=async_mock.MagicMock(value="v0.7.3")),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(
                return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
            ),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            session = await conductor.root_profile.session()

            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )

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

    async def test_startup_version_no_upgrade_add_record(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(return_value=async_mock.MagicMock(value="v0.8.1")),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=[]),
        ), async_mock.patch.object(
            test_module,
            "add_version_record",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            await conductor.stop()

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=[]),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            await conductor.stop()

    async def test_startup_version_force_upgrade(self):
        test_settings = {
            "admin.webhook_urls": ["http://sample.webhook.ca"],
            "upgrade.from_version": "v0.7.5",
            "upgrade.force_upgrade": True,
        }
        builder: ContextBuilder = StubContextBuilder(test_settings)
        conductor = test_module.Conductor(builder)
        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(return_value=async_mock.MagicMock(value="v0.8.0")),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=["v0.8.0-rc1", "v8.0.0", "v0.8.1-rc1"]),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            await conductor.stop()

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(return_value=async_mock.MagicMock(value="v0.7.0")),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=["v0.7.2", "v0.7.3", "v0.7.4"]),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            await conductor.stop()

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(side_effect=StorageNotFoundError()),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=["v0.8.0-rc1", "v8.0.0", "v0.8.1-rc1"]),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            await conductor.setup()
            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            mock_logger.print_banner.assert_called_once()
            await conductor.stop()

    async def test_startup_version_record_not_exists(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(side_effect=StorageNotFoundError()),
        ), async_mock.patch.object(
            test_module,
            "get_upgrade_version_list",
            async_mock.MagicMock(return_value=["v0.8.0-rc1", "v8.0.0", "v0.8.1-rc1"]),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            session = await conductor.root_profile.session()

            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )

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

    async def test_startup_admin_server_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            test_module, "AdminServer", async_mock.MagicMock()
        ) as mock_admin_server:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            mock_admin_server.side_effect = ValueError()
            with self.assertRaises(ValueError):
                await conductor.setup()

    async def test_startup_no_public_did(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.enqueue_message = async_mock.AsyncMock()
            mock_outbound_mgr.return_value.start = async_mock.AsyncMock()
            mock_outbound_mgr.return_value.stop = async_mock.AsyncMock()
            await conductor.setup()

            mock_inbound_mgr.return_value.setup.assert_awaited_once()
            mock_outbound_mgr.return_value.setup.assert_awaited_once()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}

            # Doesn't raise
            await conductor.start()

            mock_inbound_mgr.return_value.start.assert_awaited_once_with()
            mock_outbound_mgr.return_value.start.assert_awaited_once_with()

            mock_logger.print_banner.assert_called_once()

            await conductor.stop()

            mock_inbound_mgr.return_value.stop.assert_awaited_once_with()
            mock_outbound_mgr.return_value.stop.assert_awaited_once_with()

    async def test_stats(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger:
            mock_inbound_mgr.return_value.sessions = ["dummy"]
            mock_outbound_mgr.return_value.outbound_buffer = [
                async_mock.MagicMock(state=QueuedOutboundMessage.STATE_ENCODE),
                async_mock.MagicMock(state=QueuedOutboundMessage.STATE_DELIVER),
            ]
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }

            await conductor.setup()

            stats = await conductor.get_stats()
            assert all(
                x in stats
                for x in [
                    "in_sessions",
                    "out_encode",
                    "out_deliver",
                    "task_active",
                    "task_done",
                    "task_failed",
                    "task_pending",
                ]
            )

    async def test_inbound_message_handler(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            conductor.dispatcher, "queue_message", autospec=True
        ) as mock_dispatch_q:
            message_body = "{}"
            receipt = MessageReceipt(direct_response_mode="snail mail")
            message = InboundMessage(message_body, receipt)

            conductor.inbound_message_router(
                conductor.context, message, can_respond=False
            )

            mock_dispatch_q.assert_called_once()
            assert mock_dispatch_q.call_args[0][0] is conductor.context
            assert mock_dispatch_q.call_args[0][1] is message
            assert mock_dispatch_q.call_args[0][2] == conductor.outbound_message_router
            assert callable(mock_dispatch_q.call_args[0][3])

    async def test_inbound_message_handler_ledger_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            conductor.dispatcher, "queue_message", autospec=True
        ) as mock_dispatch_q, async_mock.patch.object(
            conductor.admin_server, "notify_fatal_error", async_mock.MagicMock()
        ) as mock_notify:
            mock_dispatch_q.side_effect = test_module.LedgerConfigError("ledger down")

            message_body = "{}"
            receipt = MessageReceipt(direct_response_mode="snail mail")
            message = InboundMessage(message_body, receipt)

            with self.assertRaises(test_module.LedgerConfigError):
                conductor.inbound_message_router(
                    conductor.context, message, can_respond=False
                )

            mock_dispatch_q.assert_called_once()
            mock_notify.assert_called_once()

    async def test_outbound_message_handler_return_route(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        test_to_verkey = "test-to-verkey"
        test_from_verkey = "test-from-verkey"
        await conductor.setup()

        bus = conductor.root_profile.inject(EventBus)

        payload = "{}"
        message = OutboundMessage(payload=payload)
        message.reply_to_verkey = test_to_verkey
        receipt = MessageReceipt()
        receipt.recipient_verkey = test_from_verkey
        inbound = InboundMessage("[]", receipt)

        with async_mock.patch.object(
            conductor.inbound_transport_manager, "return_to_session"
        ) as mock_return:
            mock_return.return_value = True

            status = await conductor.outbound_message_router(
                conductor.root_profile, message
            )
            assert status == OutboundSendStatus.SENT_TO_SESSION
            assert bus.events
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message
            mock_return.assert_called_once_with(message)

    async def test_outbound_message_handler_with_target(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            bus = conductor.root_profile.inject(EventBus)

            payload = "{}"
            target = ConnectionTarget(
                endpoint="endpoint", recipient_keys=(), routing_keys=(), sender_key=""
            )
            message = OutboundMessage(payload=payload, target=target)

            status = await conductor.outbound_message_router(
                conductor.root_profile, message
            )
            assert status == OutboundSendStatus.QUEUED_FOR_DELIVERY
            assert bus.events
            print(bus.events)
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message
            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_outbound_message_handler_with_connection(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            bus = conductor.root_profile.inject(EventBus)

            payload = "{}"
            connection_id = "connection_id"
            message = OutboundMessage(payload=payload, connection_id=connection_id)

            status = await conductor.outbound_message_router(
                conductor.root_profile, message
            )

            assert status == OutboundSendStatus.QUEUED_FOR_DELIVERY
            assert bus.events
            print(bus.events)
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message

            conn_mgr.return_value.get_connection_targets.assert_awaited_once_with(
                connection_id=connection_id
            )
            assert (
                message.target_list
                is conn_mgr.return_value.get_connection_targets.return_value
            )

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_outbound_message_handler_with_verkey_no_target(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            bus = conductor.root_profile.inject(EventBus)

            payload = "{}"
            message = OutboundMessage(
                payload=payload, reply_to_verkey=TestDIDs.test_verkey
            )

            status = await conductor.outbound_message_router(
                conductor.root_profile,
                message,
                inbound=async_mock.MagicMock(
                    receipt=async_mock.MagicMock(recipient_verkey=TestDIDs.test_verkey)
                ),
            )

            assert status == OutboundSendStatus.QUEUED_FOR_DELIVERY
            assert bus.events
            print(bus.events)
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_handle_nots(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", async_mock.MagicMock()
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value = async_mock.MagicMock(
                setup=async_mock.AsyncMock(),
                enqueue_message=async_mock.AsyncMock(),
            )

            payload = "{}"
            message = OutboundMessage(
                payload=payload,
                connection_id="dummy-conn-id",
                reply_to_verkey=TestDIDs.test_verkey,
            )

            await conductor.setup()

            conductor.handle_not_returned(conductor.root_profile, message)

            with async_mock.patch.object(
                test_module, "ConnectionManager"
            ) as mock_conn_mgr, async_mock.patch.object(
                conductor.dispatcher, "run_task", async_mock.MagicMock()
            ) as mock_run_task:
                mock_conn_mgr.return_value.get_connection_targets = (
                    async_mock.AsyncMock()
                )
                mock_run_task.side_effect = test_module.ConnectionManagerError()
                await conductor.queue_outbound(conductor.root_profile, message)
                mock_outbound_mgr.return_value.enqueue_message.assert_not_called()

                message.connection_id = None
                mock_outbound_mgr.return_value.enqueue_message.side_effect = (
                    test_module.OutboundDeliveryError()
                )
                await conductor.queue_outbound(conductor.root_profile, message)
                mock_run_task.assert_called_once()

    async def test_handle_outbound_queue(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        encoded_outbound_message_mock = async_mock.MagicMock(payload="message_payload")

        payload = "{}"
        message = OutboundMessage(
            payload=payload,
            connection_id="dummy-conn-id",
            target=async_mock.MagicMock(endpoint="endpoint"),
            reply_to_verkey=TestDIDs.test_verkey,
        )
        await conductor.setup()
        await conductor.queue_outbound(conductor.root_profile, message)

    async def test_handle_not_returned_ledger_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        with async_mock.patch.object(
            conductor.dispatcher, "run_task", async_mock.MagicMock()
        ) as mock_dispatch_run, async_mock.patch.object(
            conductor, "queue_outbound", async_mock.AsyncMock()
        ) as mock_queue, async_mock.patch.object(
            conductor.admin_server, "notify_fatal_error", async_mock.MagicMock()
        ) as mock_notify:
            mock_dispatch_run.side_effect = test_module.LedgerConfigError(
                "No such ledger"
            )

            payload = "{}"
            message = OutboundMessage(
                payload=payload,
                connection_id="dummy-conn-id",
                reply_to_verkey=TestDIDs.test_verkey,
            )

            with self.assertRaises(test_module.LedgerConfigError):
                conductor.handle_not_returned(conductor.root_profile, message)

            mock_dispatch_run.assert_called_once()
            mock_notify.assert_called_once()

    async def test_queue_outbound_ledger_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            test_module, "ConnectionManager", autospec=True
        ) as conn_mgr, async_mock.patch.object(
            conductor.dispatcher, "run_task", async_mock.MagicMock()
        ) as mock_dispatch_run, async_mock.patch.object(
            conductor.admin_server, "notify_fatal_error", async_mock.MagicMock()
        ) as mock_notify:
            conn_mgr.return_value.get_connection_targets = async_mock.AsyncMock()
            mock_dispatch_run.side_effect = test_module.LedgerConfigError(
                "No such ledger"
            )

            payload = "{}"
            message = OutboundMessage(
                payload=payload,
                connection_id="dummy-conn-id",
                reply_to_verkey=TestDIDs.test_verkey,
            )

            with self.assertRaises(test_module.LedgerConfigError):
                await conductor.queue_outbound(conductor.root_profile, message)

            mock_dispatch_run.assert_called_once()
            mock_notify.assert_called_once()

    async def test_admin(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"admin.enabled": "1"})
        conductor = test_module.Conductor(builder)
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        admin = conductor.context.inject(BaseAdminServer)
        assert admin is conductor.admin_server

        session = await conductor.root_profile.session()
        wallet = session.inject(BaseWallet)
        await wallet.create_public_did(
            SOV,
            ED25519,
        )

        with async_mock.patch.object(
            admin, "start", autospec=True
        ) as admin_start, async_mock.patch.object(
            admin, "stop", autospec=True
        ) as admin_stop, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            admin_start.assert_awaited_once_with()

            await conductor.stop()
            admin_stop.assert_awaited_once_with()

    async def test_admin_startx(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(
            {
                "admin.enabled": "1",
                "debug.print_invitation": True,
                "debug.print_connections_invitation": True,
            }
        )
        conductor = test_module.Conductor(builder)
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        admin = conductor.context.inject(BaseAdminServer)
        assert admin is conductor.admin_server

        session = await conductor.root_profile.session()
        wallet = session.inject(BaseWallet)
        await wallet.create_public_did(
            SOV,
            ED25519,
        )

        with async_mock.patch.object(
            admin, "start", autospec=True
        ) as admin_start, async_mock.patch.object(
            admin, "stop", autospec=True
        ) as admin_stop, async_mock.patch.object(
            test_module, "OutOfBandManager"
        ) as oob_mgr, async_mock.patch.object(
            test_module, "ConnectionManager"
        ) as conn_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            admin_start.side_effect = KeyError("trouble")
            oob_mgr.return_value.create_invitation = async_mock.AsyncMock(
                side_effect=KeyError("double trouble")
            )
            conn_mgr.return_value.create_invitation = async_mock.AsyncMock(
                side_effect=KeyError("triple trouble")
            )
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
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

    async def test_start_static(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "ConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ), async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )

            mock_mgr.return_value.create_static_connection = async_mock.AsyncMock()
            await conductor.start()
            mock_mgr.return_value.create_static_connection.assert_awaited_once()

    async def test_start_x_in(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "ConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            test_module, "InboundTransportManager"
        ) as mock_intx_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_intx_mgr.return_value = async_mock.MagicMock(
                setup=async_mock.AsyncMock(),
                start=async_mock.AsyncMock(side_effect=KeyError("trouble")),
            )
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = async_mock.AsyncMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_start_x_out_a(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "ConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager"
        ) as mock_outx_mgr:
            mock_outx_mgr.return_value = async_mock.MagicMock(
                setup=async_mock.AsyncMock(),
                start=async_mock.AsyncMock(side_effect=KeyError("trouble")),
                registered_transports={"test": async_mock.MagicMock(schemes=["http"])},
            )
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = async_mock.AsyncMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_start_x_out_b(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "ConnectionManager"
        ) as mock_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager"
        ) as mock_outx_mgr:
            mock_outx_mgr.return_value = async_mock.MagicMock(
                setup=async_mock.AsyncMock(),
                start=async_mock.AsyncMock(side_effect=KeyError("trouble")),
                stop=async_mock.AsyncMock(),
                registered_transports={},
                enqueue_message=async_mock.AsyncMock(),
            )
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = async_mock.AsyncMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_dispatch_complete_non_fatal_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        message_body = "{}"
        receipt = MessageReceipt(direct_response_mode="snail mail")
        message = InboundMessage(message_body, receipt)
        exc = KeyError("sample exception")
        mock_task = async_mock.MagicMock(
            exc_info=(type(exc), exc, exc.__traceback__),
            ident="abc",
            timing={
                "queued": 1234567890,
                "unqueued": 1234567899,
                "started": 1234567901,
                "ended": 1234567999,
            },
        )

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            conductor.admin_server, "notify_fatal_error", async_mock.MagicMock()
        ) as mock_notify:
            conductor.dispatch_complete(message, mock_task)
            mock_notify.assert_not_called()

    async def test_dispatch_complete_fatal_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        message_body = "{}"
        receipt = MessageReceipt(direct_response_mode="snail mail")
        message = InboundMessage(message_body, receipt)
        exc = test_module.LedgerTransactionError("Ledger is wobbly")
        mock_task = async_mock.MagicMock(
            exc_info=(type(exc), exc, exc.__traceback__),
            ident="abc",
            timing={
                "queued": 1234567890,
                "unqueued": 1234567899,
                "started": 1234567901,
                "ended": 1234567999,
            },
        )

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            conductor.admin_server, "notify_fatal_error", async_mock.MagicMock()
        ) as mock_notify:
            conductor.dispatch_complete(message, mock_task)
            mock_notify.assert_called_once_with()

    async def test_print_invite_connection(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(
            {
                "debug.print_invitation": True,
                "debug.print_connections_invitation": True,
                "invite_base_url": "http://localhost",
            }
        )
        conductor = test_module.Conductor(builder)

        with async_mock.patch(
            "sys.stdout", new=StringIO()
        ) as captured, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ), async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            session = await conductor.root_profile.session()
            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )

            await conductor.start()
            await conductor.stop()
            value = captured.getvalue()
            assert "http://localhost?oob=" in value
            assert "http://localhost?c_i=" in value

    async def test_clear_default_mediator(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.clear": True})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            test_module,
            "MediationManager",
            return_value=async_mock.MagicMock(
                clear_default_mediator=async_mock.AsyncMock()
            ),
        ) as mock_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_mgr.return_value.clear_default_mediator.assert_called_once()

    async def test_set_default_mediator(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.default_id": "test-id"})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            test_module,
            "MediationManager",
            return_value=async_mock.MagicMock(
                set_default_mediator_by_id=async_mock.AsyncMock()
            ),
        ) as mock_mgr, async_mock.patch.object(
            MediationRecord, "retrieve_by_id", async_mock.AsyncMock()
        ), async_mock.patch.object(
            test_module,
            "LOGGER",
            async_mock.MagicMock(
                exception=async_mock.MagicMock(
                    side_effect=Exception("This method should not have been called")
                )
            ),
        ), async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_mgr.return_value.set_default_mediator_by_id.assert_called_once()

    async def test_set_default_mediator_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.default_id": "test-id"})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            MediationRecord,
            "retrieve_by_id",
            async_mock.AsyncMock(side_effect=Exception()),
        ), async_mock.patch.object(
            test_module, "LOGGER"
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_logger.exception.assert_called_once()

    async def test_webhook_router(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings(
            {"debug.print_invitation": True, "invite_base_url": "http://localhost"}
        )
        conductor = test_module.Conductor(builder)

        test_topic = "test-topic"
        test_payload = {"test": "payload"}
        test_endpoint = "http://example"
        test_attempts = 2

        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        with async_mock.patch.object(
            conductor.outbound_transport_manager, "enqueue_webhook"
        ) as mock_enqueue:
            conductor.webhook_router(
                test_topic, test_payload, test_endpoint, test_attempts
            )
            mock_enqueue.assert_called_once_with(
                test_topic, test_payload, test_endpoint, test_attempts, None
            )

        # swallow error
        with async_mock.patch.object(
            conductor.outbound_transport_manager,
            "enqueue_webhook",
            side_effect=OutboundDeliveryError,
        ) as mock_enqueue:
            conductor.webhook_router(
                test_topic, test_payload, test_endpoint, test_attempts
            )
            mock_enqueue.assert_called_once_with(
                test_topic, test_payload, test_endpoint, test_attempts, None
            )

    async def test_shutdown_multitenant_profiles(self):
        builder: ContextBuilder = StubContextBuilder(
            {**self.test_settings, "multitenant.enabled": True}
        )
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LoggingConfigurator", autospec=True
        ) as mock_logger:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            multitenant_mgr = conductor.context.inject(BaseMultitenantManager)
            assert isinstance(multitenant_mgr, MultitenantManager)

            multitenant_mgr._profiles.put(
                "test1",
                async_mock.MagicMock(close=async_mock.AsyncMock()),
            )
            multitenant_mgr._profiles.put(
                "test2",
                async_mock.MagicMock(close=async_mock.AsyncMock()),
            )

            await conductor.stop()

            multitenant_mgr._profiles.profiles["test1"].close.assert_called_once_with()
            multitenant_mgr._profiles.profiles["test2"].close.assert_called_once_with()


def get_invite_store_mock(
    invite_string: str, invite_already_used: bool = False
) -> async_mock.MagicMock:
    unused_invite = MediationInviteRecord(invite_string, invite_already_used)
    used_invite = MediationInviteRecord(invite_string, used=True)

    return async_mock.MagicMock(
        get_mediation_invite_record=async_mock.AsyncMock(return_value=unused_invite),
        mark_default_invite_as_used=async_mock.AsyncMock(return_value=used_invite),
    )


class TestConductorMediationSetup(IsolatedAsyncioTestCase, Config):
    """
    Test related with setting up mediation from given arguments or stored invitation.
    """

    def __get_mediator_config(
        self, invite_string: str, connections_invite: bool = False
    ) -> ContextBuilder:
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.invite": invite_string})
        if connections_invite:
            builder.update_settings({"mediation.connections_invite": True})

        return builder

    @async_mock.patch.object(
        test_module,
        "MediationInviteStore",
        return_value=get_invite_store_mock("test-invite"),
    )
    @async_mock.patch.object(test_module.ConnectionInvitation, "from_url")
    async def test_mediator_invitation_0160(self, mock_from_url, _):
        conductor = test_module.Conductor(
            self.__get_mediator_config("test-invite", True)
        )
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        mock_conn_record = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module,
            "ConnectionManager",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    receive_invitation=async_mock.AsyncMock(
                        return_value=mock_conn_record
                    )
                )
            ),
        ) as mock_mgr, async_mock.patch.object(
            mock_conn_record, "metadata_set", async_mock.AsyncMock()
        ), async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_from_url.assert_called_once_with("test-invite")
            mock_mgr.return_value.receive_invitation.assert_called_once()

    @async_mock.patch.object(
        test_module,
        "MediationInviteStore",
        return_value=get_invite_store_mock("test-invite"),
    )
    @async_mock.patch.object(test_module.InvitationMessage, "from_url")
    async def test_mediator_invitation_0434(self, mock_from_url, _):
        conductor = test_module.Conductor(
            self.__get_mediator_config("test-invite", False)
        )
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        conductor.root_profile.context.update_settings(
            {"mediation.connections_invite": False}
        )
        conn_record = ConnRecord(
            invitation_key="3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
            their_label="Hello",
            their_role=ConnRecord.Role.RESPONDER.rfc160,
            alias="Bob",
        )
        conn_record.accept = ConnRecord.ACCEPT_MANUAL
        await conn_record.save(await conductor.root_profile.session())
        invitation = test_module.InvitationMessage()
        oob_record = OobRecord(
            invitation=invitation,
            invi_msg_id=invitation._id,
            role=OobRecord.ROLE_RECEIVER,
            connection_id=conn_record.connection_id,
            state=OobRecord.STATE_INITIAL,
        )
        with async_mock.patch.object(
            test_module,
            "OutOfBandManager",
            async_mock.MagicMock(
                return_value=async_mock.MagicMock(
                    receive_invitation=async_mock.AsyncMock(return_value=oob_record)
                )
            ),
        ) as mock_mgr, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            assert not conductor.root_profile.settings["mediation.connections_invite"]
            await conductor.start()
            await conductor.stop()
            mock_from_url.assert_called_once_with("test-invite")
            mock_mgr.return_value.receive_invitation.assert_called_once()

    @async_mock.patch.object(test_module, "MediationInviteStore")
    @async_mock.patch.object(test_module.ConnectionInvitation, "from_url")
    async def test_mediation_invitation_should_use_stored_invitation(
        self, patched_from_url, patched_invite_store
    ):
        """
        Conductor should store the mediation invite if it differs from the stored one or
        if the stored one was not used yet.

        Using a mediation invitation should clear the previously set default mediator.
        """
        # given
        invite_string = "test-invite"

        conductor = test_module.Conductor(
            self.__get_mediator_config(invite_string, True)
        )
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        mock_conn_record = async_mock.MagicMock()
        mocked_store = get_invite_store_mock(invite_string)
        patched_invite_store.return_value = mocked_store

        connection_manager_mock = async_mock.MagicMock(
            receive_invitation=async_mock.AsyncMock(return_value=mock_conn_record)
        )
        mock_mediation_manager = async_mock.MagicMock(
            clear_default_mediator=async_mock.AsyncMock()
        )

        # when
        with async_mock.patch.object(
            test_module, "ConnectionManager", return_value=connection_manager_mock
        ), async_mock.patch.object(
            mock_conn_record, "metadata_set", async_mock.AsyncMock()
        ), async_mock.patch.object(
            test_module, "MediationManager", return_value=mock_mediation_manager
        ), async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()

            # then
            mocked_store.get_mediation_invite_record.assert_called_with(invite_string)

            connection_manager_mock.receive_invitation.assert_called_once()
            patched_from_url.assert_called_with(invite_string)
            mock_mediation_manager.clear_default_mediator.assert_called_once()

    @async_mock.patch.object(test_module, "MediationInviteStore")
    @async_mock.patch.object(test_module, "ConnectionManager")
    async def test_mediation_invitation_should_not_create_connection_for_old_invitation(
        self, patched_connection_manager, patched_invite_store
    ):
        # given
        invite_string = "test-invite"

        conductor = test_module.Conductor(
            self.__get_mediator_config(invite_string, True)
        )
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        invite_store_mock = get_invite_store_mock(invite_string, True)
        patched_invite_store.return_value = invite_store_mock

        connection_manager_mock = async_mock.MagicMock(
            receive_invitation=async_mock.AsyncMock()
        )
        patched_connection_manager.return_value = connection_manager_mock
        with async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            # when
            await conductor.start()
            await conductor.stop()

            # then
            invite_store_mock.get_mediation_invite_record.assert_called_with(
                invite_string
            )
            connection_manager_mock.receive_invitation.assert_not_called()

    @async_mock.patch.object(
        test_module,
        "MediationInviteStore",
        return_value=get_invite_store_mock("test-invite"),
    )
    async def test_mediator_invitation_x(self, _):
        conductor = test_module.Conductor(
            self.__get_mediator_config("test-invite", True)
        )
        with async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with async_mock.patch.object(
            test_module.ConnectionInvitation,
            "from_url",
            async_mock.MagicMock(side_effect=Exception()),
        ) as mock_from_url, async_mock.patch.object(
            test_module, "LOGGER"
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(
                return_value=async_mock.MagicMock(value=f"v{__version__}")
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_from_url.assert_called_once_with("test-invite")
            mock_logger.exception.assert_called_once()

    async def test_setup_ledger_both_multiple_and_base(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"ledger.genesis_transactions": "..."})
        builder.update_settings({"ledger.ledger_config_list": [{"...": "..."}]})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module,
            "load_multiple_genesis_transactions_from_config",
            async_mock.AsyncMock(),
        ) as mock_multiple_genesis_load, async_mock.patch.object(
            test_module, "get_genesis_transactions", async_mock.AsyncMock()
        ) as mock_genesis_load, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_multiple_genesis_load.assert_called_once()
            mock_genesis_load.assert_called_once()

    async def test_setup_ledger_only_base(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"ledger.genesis_transactions": "..."})
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "get_genesis_transactions", async_mock.AsyncMock()
        ) as mock_genesis_load, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr:
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_genesis_load.assert_called_once()

    async def test_startup_x_no_storage_version(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        with async_mock.patch.object(
            test_module, "InboundTransportManager", autospec=True
        ) as mock_inbound_mgr, async_mock.patch.object(
            test_module, "OutboundTransportManager", autospec=True
        ) as mock_outbound_mgr, async_mock.patch.object(
            test_module, "LOGGER"
        ) as mock_logger, async_mock.patch.object(
            BaseStorage,
            "find_record",
            async_mock.AsyncMock(side_effect=StorageNotFoundError()),
        ), async_mock.patch.object(
            test_module,
            "upgrade",
            async_mock.AsyncMock(),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": async_mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            session = await conductor.root_profile.session()

            wallet = session.inject(BaseWallet)
            await wallet.create_public_did(
                SOV,
                ED25519,
            )

            mock_inbound_mgr.return_value.setup.assert_awaited_once()
            mock_outbound_mgr.return_value.setup.assert_awaited_once()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
