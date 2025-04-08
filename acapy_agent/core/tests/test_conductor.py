from unittest import IsolatedAsyncioTestCase

from ...admin.base_server import BaseAdminServer
from ...askar.profile import AskarProfileManager
from ...config.base_context import ContextBuilder
from ...config.injection_context import InjectionContext
from ...connections.base_manager import BaseConnectionManager
from ...connections.models.conn_record import ConnRecord
from ...connections.models.connection_target import ConnectionTarget
from ...connections.models.diddoc import DIDDoc, PublicKey, PublicKeyType, Service
from ...core.event_bus import EventBus, MockEventBus
from ...core.profile import ProfileManager
from ...core.protocol_registry import ProtocolRegistry
from ...ledger.base import BaseLedger
from ...multitenant.base import BaseMultitenantManager
from ...multitenant.manager import MultitenantManager
from ...protocols.coordinate_mediation.mediation_invite_store import MediationInviteRecord
from ...protocols.coordinate_mediation.v1_0.models.mediation_record import MediationRecord
from ...protocols.out_of_band.v1_0.models.oob_record import OobRecord
from ...resolver.did_resolver import DIDResolver
from ...storage.base import BaseStorage
from ...storage.error import StorageNotFoundError
from ...storage.record import StorageRecord
from ...storage.type import RECORD_TYPE_ACAPY_STORAGE_TYPE
from ...tests import mock
from ...transport.inbound.manager import InboundTransportManager
from ...transport.inbound.message import InboundMessage
from ...transport.inbound.receipt import MessageReceipt
from ...transport.outbound.base import OutboundDeliveryError, QueuedOutboundMessage
from ...transport.outbound.message import OutboundMessage
from ...transport.outbound.status import OutboundSendStatus
from ...transport.pack_format import PackWireFormat
from ...transport.wire_format import BaseWireFormat
from ...utils.stats import Collector
from ...utils.testing import create_test_profile
from ...version import RECORD_TYPE_ACAPY_VERSION
from ...wallet.did_info import DIDInfo
from ...wallet.did_method import SOV, DIDMethods
from ...wallet.key_type import ED25519, KeyTypes
from .. import conductor as test_module


class Config:
    test_settings = {
        "admin.webhook_urls": ["http://sample.webhook.ca"],
        "wallet.type": "askar",
        "wallet.key": "insecure",
    }
    test_settings_admin = {
        "admin.webhook_urls": ["http://sample.webhook.ca"],
        "admin.enabled": True,
        "wallet.type": "askar",
        "wallet.key": "insecure",
        "auto_provision": True,
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
        self.wire_format = mock.create_autospec(PackWireFormat())

    async def build_context(self) -> InjectionContext:
        context = InjectionContext(settings=self.settings, enforce_typing=False)
        context.injector.bind_instance(ProfileManager, AskarProfileManager())
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        context.injector.bind_instance(BaseWireFormat, self.wire_format)
        context.injector.bind_instance(DIDMethods, DIDMethods())
        context.injector.bind_instance(DIDResolver, DIDResolver([]))
        context.injector.bind_instance(EventBus, MockEventBus())
        context.injector.bind_instance(KeyTypes, KeyTypes())
        context.injector.bind_instance(
            InboundTransportManager,
            mock.MagicMock(InboundTransportManager, autospec=True),
        )
        context.injector.bind_instance(BaseConnectionManager, mock.MagicMock())
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(
                    return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module, "LoggingConfigurator", autospec=True
            ) as mock_logger,
        ):
            await conductor.setup()

            mock_inbound_mgr.return_value.setup.assert_awaited_once()
            mock_outbound_mgr.return_value.setup.assert_awaited_once()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}

            async with test_profile.session() as session:
                storage = session.inject(BaseStorage)
                await storage.add_record(
                    StorageRecord(RECORD_TYPE_ACAPY_VERSION, "v0.7.3")
                )

                await conductor.start()

                mock_inbound_mgr.return_value.start.assert_awaited_once_with()
                mock_outbound_mgr.return_value.start.assert_awaited_once_with()

                mock_logger.print_banner.assert_called_once()

                upgrade_record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_VERSION, tag_query={}
                )

                assert upgrade_record != "v0.7.3"

                await conductor.stop()

                mock_inbound_mgr.return_value.stop.assert_awaited_once_with()
                mock_outbound_mgr.return_value.stop.assert_awaited_once_with()

    async def test_startup_version_no_upgrade_add_record(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(
                    return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            await conductor.stop()

    async def test_startup_version_force_upgrade(self):
        test_settings = {
            "admin.webhook_urls": ["http://sample.webhook.ca"],
            "upgrade.from_version": "v0.7.5",
            "upgrade.force_upgrade": True,
            "wallet.type": "askar",
            "wallet.key": "insecure",
        }
        builder: ContextBuilder = StubContextBuilder(test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(
                    return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
                ),
            ),
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }

            async with test_profile.session() as session:
                storage = session.inject(BaseStorage)
                await storage.add_record(
                    StorageRecord(RECORD_TYPE_ACAPY_VERSION, "v0.7.3")
                )

                await conductor.setup()
                mock_inbound_mgr.return_value.registered_transports = {}
                mock_outbound_mgr.return_value.registered_transports = {}
                await conductor.start()
                await conductor.stop()

        test_profile = await create_test_profile(None, await builder.build_context())
        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module, "LoggingConfigurator", autospec=True
            ) as mock_logger,
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(return_value=["v0.8.0-rc1", "v8.0.0", "v0.8.1-rc1"]),
            ),
            mock.patch.object(test_module, "ledger_config"),
            mock.patch.object(test_module.Conductor, "check_for_valid_wallet_type"),
        ):
            await conductor.setup()
            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            await conductor.start()
            mock_logger.print_banner.assert_called_once()
            await conductor.stop()

    async def test_startup_version_record_not_exists(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module, "LoggingConfigurator", autospec=True
            ) as mock_logger,
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
            mock.patch.object(
                BaseStorage,
                "find_record",
                mock.CoroutineMock(
                    side_effect=[mock.MagicMock(value="askar"), StorageNotFoundError()]
                ),
            ),
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(return_value=["v0.8.0-rc1", "v8.0.0", "v0.8.1-rc1"]),
            ),
            mock.patch.object(
                test_module,
                "upgrade",
                mock.CoroutineMock(),
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
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

    async def test_startup_admin_server_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(test_module, "LoggingConfigurator", autospec=True),
            mock.patch.object(
                test_module, "AdminServer", mock.MagicMock()
            ) as mock_admin_server,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            mock_admin_server.side_effect = ValueError()
            with self.assertRaises(ValueError):
                await conductor.setup()

    async def test_startup_no_public_did(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module, "LoggingConfigurator", autospec=True
            ) as mock_logger,
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.enqueue_message = mock.CoroutineMock()
            mock_outbound_mgr.return_value.start = mock.CoroutineMock()
            mock_outbound_mgr.return_value.stop = mock.CoroutineMock()
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
        ):
            mock_inbound_mgr.return_value.sessions = ["dummy"]
            mock_outbound_mgr.return_value.outbound_buffer = [
                mock.MagicMock(state=QueuedOutboundMessage.STATE_ENCODE),
                mock.MagicMock(state=QueuedOutboundMessage.STATE_DELIVER),
            ]
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
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
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with mock.patch.object(
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with (
            mock.patch.object(
                conductor.dispatcher, "queue_message", autospec=True
            ) as mock_dispatch_q,
            mock.patch.object(test_module, "LOGGER", mock.MagicMock()) as mock_logger,
        ):
            mock_dispatch_q.side_effect = test_module.LedgerConfigError("ledger down")

            message_body = "{}"
            receipt = MessageReceipt(direct_response_mode="snail mail")
            message = InboundMessage(message_body, receipt)

            with self.assertRaises(test_module.LedgerConfigError):
                conductor.inbound_message_router(
                    conductor.context, message, can_respond=False
                )

            mock_dispatch_q.assert_called_once()
            mock_logger.error.assert_called_once()

    async def test_outbound_message_handler_return_route(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        test_to_verkey = "test-to-verkey"
        test_from_verkey = "test-from-verkey"
        test_profile = await create_test_profile(None, await builder.build_context())

        with mock.patch.object(
            test_module,
            "wallet_config",
            return_value=(
                test_profile,
                DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
            ),
        ):
            await conductor.setup()

        bus = conductor.root_profile.inject(EventBus)

        payload = "{}"
        message = OutboundMessage(payload=payload)
        message.reply_to_verkey = test_to_verkey
        receipt = MessageReceipt()
        receipt.recipient_verkey = test_from_verkey

        with mock.patch.object(
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            assert conductor.root_profile
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
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message
            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_outbound_message_handler_with_connection(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            conn_mgr = mock.MagicMock(autospec=True)
            conn_mgr.get_connection_targets = mock.CoroutineMock()
            conductor.context.injector.bind_instance(BaseConnectionManager, conn_mgr)

            assert conductor.root_profile
            bus = conductor.root_profile.inject(EventBus)

            payload = "{}"
            connection_id = "connection_id"
            message = OutboundMessage(payload=payload, connection_id=connection_id)

            status = await conductor.outbound_message_router(
                conductor.root_profile, message
            )

            assert status == OutboundSendStatus.QUEUED_FOR_DELIVERY
            assert bus.events
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message

            conn_mgr.get_connection_targets.assert_awaited_once_with(
                connection_id=connection_id
            )
            assert message.target_list is conn_mgr.get_connection_targets.return_value

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_outbound_message_handler_with_verkey_no_target(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
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
                inbound=mock.MagicMock(
                    receipt=mock.MagicMock(recipient_verkey=TestDIDs.test_verkey)
                ),
            )

            assert status == OutboundSendStatus.QUEUED_FOR_DELIVERY
            assert bus.events
            assert bus.events[0][1].topic == status.topic
            assert bus.events[0][1].payload == message

            mock_outbound_mgr.return_value.enqueue_message.assert_called_once_with(
                conductor.root_profile, message
            )

    async def test_handle_nots(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", mock.MagicMock()
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value = mock.MagicMock(
                setup=mock.CoroutineMock(),
                enqueue_message=mock.CoroutineMock(),
            )

            payload = "{}"
            message = OutboundMessage(
                payload=payload,
                connection_id="dummy-conn-id",
                reply_to_verkey=TestDIDs.test_verkey,
            )

            await conductor.setup()

            assert conductor.root_profile
            conductor.handle_not_returned(conductor.root_profile, message)

            mock_conn_mgr = mock.MagicMock()
            conductor.context.injector.bind_instance(BaseConnectionManager, mock_conn_mgr)
            with (
                mock.patch.object(
                    conductor.dispatcher, "run_task", mock.MagicMock()
                ) as mock_run_task,
            ):
                mock_run_task.side_effect = test_module.BaseConnectionManagerError()
                await conductor.queue_outbound(conductor.root_profile, message)

                message.connection_id = None
                await conductor.queue_outbound(conductor.root_profile, message)
                mock_run_task.assert_called_once()

    async def test_handle_outbound_queue(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        payload = "{}"
        message = OutboundMessage(
            payload=payload,
            connection_id="dummy-conn-id",
            target=mock.MagicMock(endpoint="endpoint"),
            reply_to_verkey=TestDIDs.test_verkey,
        )
        test_profile = await create_test_profile(None, await builder.build_context())

        with mock.patch.object(
            test_module,
            "wallet_config",
            return_value=(
                test_profile,
                DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
            ),
        ):
            await conductor.setup()

        await conductor.queue_outbound(conductor.root_profile, message)

    async def test_handle_not_returned_ledger_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        with (
            mock.patch.object(
                conductor.dispatcher, "run_task", mock.MagicMock()
            ) as mock_dispatch_run,
            mock.patch.object(conductor, "queue_outbound", mock.MagicMock()),
        ):
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

    async def test_queue_outbound_ledger_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        conn_mgr = mock.MagicMock()
        conductor.context.injector.bind_instance(BaseConnectionManager, conn_mgr)
        with (
            mock.patch.object(
                conductor.dispatcher, "run_task", mock.MagicMock()
            ) as mock_dispatch_run,
            mock.patch.object(test_module, "LOGGER", mock.MagicMock()) as mock_logger,
        ):
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
            mock_logger.error.assert_called_once()

    async def test_admin(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"admin.enabled": "1"})
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        admin = conductor.context.inject(BaseAdminServer)
        assert admin is conductor.admin_server

        with (
            mock.patch.object(admin, "start", autospec=True) as admin_start,
            mock.patch.object(admin, "stop", autospec=True) as admin_stop,
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
                "wallet.type": "askar",
            }
        )
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        admin = conductor.context.inject(BaseAdminServer)
        assert admin is conductor.admin_server

        with (
            mock.patch.object(admin, "start", autospec=True) as admin_start,
            mock.patch.object(admin, "stop", autospec=True) as admin_stop,
            mock.patch.object(test_module, "OutOfBandManager") as oob_mgr,
            mock.patch.object(test_module, "BaseConnectionManager") as conn_mgr,
        ):
            admin_start.side_effect = KeyError("trouble")
            oob_mgr.return_value.create_invitation = mock.CoroutineMock(
                side_effect=KeyError("double trouble")
            )
            conn_mgr.return_value.create_invitation = mock.CoroutineMock(
                side_effect=KeyError("triple trouble")
            )
            await conductor.start()
            admin_start.assert_awaited_once_with()

            await conductor.stop()
            admin_stop.assert_awaited_once_with()

    async def test_setup_collector(self):
        builder: ContextBuilder = StubCollectorContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

    async def test_start_static(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            mock_mgr.return_value.create_static_connection = mock.CoroutineMock(
                return_value=(None, None, mock.MagicMock())
            )
            await conductor.start()
            mock_mgr.return_value.create_static_connection.assert_awaited_once()

    async def test_start_x_in(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr,
            mock.patch.object(test_module, "InboundTransportManager") as mock_intx_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_intx_mgr.return_value = mock.MagicMock(
                setup=mock.CoroutineMock(),
                start=mock.CoroutineMock(side_effect=KeyError("trouble")),
            )
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = mock.CoroutineMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_start_x_out_a(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr,
            mock.patch.object(test_module, "OutboundTransportManager") as mock_outx_mgr,
        ):
            mock_outx_mgr.return_value = mock.MagicMock(
                setup=mock.CoroutineMock(),
                start=mock.CoroutineMock(side_effect=KeyError("trouble")),
                registered_transports={"test": mock.MagicMock(schemes=["http"])},
            )
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = mock.CoroutineMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_start_x_out_b(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"debug.test_suite_endpoint": True})
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(test_module, "BaseConnectionManager") as mock_mgr,
            mock.patch.object(test_module, "OutboundTransportManager") as mock_outx_mgr,
        ):
            mock_outx_mgr.return_value = mock.MagicMock(
                setup=mock.CoroutineMock(),
                start=mock.CoroutineMock(side_effect=KeyError("trouble")),
                stop=mock.CoroutineMock(),
                registered_transports={},
                enqueue_message=mock.CoroutineMock(),
            )
            await conductor.setup()
            mock_mgr.return_value.create_static_connection = mock.CoroutineMock()
            with self.assertRaises(KeyError):
                await conductor.start()

    async def test_dispatch_complete_non_fatal_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        message_body = "{}"
        receipt = MessageReceipt(direct_response_mode="snail mail")
        message = InboundMessage(message_body, receipt)
        exc = StorageNotFoundError("sample exception")
        mock_task = mock.MagicMock(
            exc_info=(type(exc), exc, exc.__traceback__),
            ident="abc",
            timing={
                "queued": 1234567890,
                "unqueued": 1234567899,
                "started": 1234567901,
                "ended": 1234567999,
            },
        )

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with mock.patch.object(
            conductor.admin_server, "notify_fatal_error", mock.MagicMock()
        ) as mock_notify:
            conductor.dispatch_complete(message, mock_task)
            mock_notify.assert_not_called()

    async def test_dispatch_complete_ledger_error_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings_admin)
        conductor = test_module.Conductor(builder)

        message_body = "{}"
        receipt = MessageReceipt(direct_response_mode="snail mail")
        message = InboundMessage(message_body, receipt)
        exc = test_module.LedgerTransactionError("Ledger is wobbly")
        mock_task = mock.MagicMock(
            exc_info=(type(exc), exc, exc.__traceback__),
            ident="abc",
            timing={
                "queued": 1234567890,
                "unqueued": 1234567899,
                "started": 1234567901,
                "ended": 1234567999,
            },
        )

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with mock.patch.object(test_module, "LOGGER", mock.MagicMock()) as mock_logger:
            conductor.dispatch_complete(message, mock_task)
            mock_logger.error.assert_called_once()

    async def test_clear_default_mediator(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.clear": True})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with mock.patch.object(
            test_module,
            "MediationManager",
            return_value=mock.MagicMock(clear_default_mediator=mock.CoroutineMock()),
        ) as mock_mgr:
            await conductor.start()
            await conductor.stop()
            mock_mgr.return_value.clear_default_mediator.assert_called_once()

    async def test_set_default_mediator(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.default_id": "test-id"})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with (
            mock.patch.object(
                test_module,
                "MediationManager",
                return_value=mock.MagicMock(
                    set_default_mediator_by_id=mock.CoroutineMock()
                ),
            ) as mock_mgr,
            mock.patch.object(MediationRecord, "retrieve_by_id", mock.CoroutineMock()),
            mock.patch.object(
                test_module,
                "LOGGER",
                mock.MagicMock(
                    exception=mock.MagicMock(
                        side_effect=Exception("This method should not have been called")
                    )
                ),
            ),
        ):
            await conductor.start()
            await conductor.stop()
            mock_mgr.return_value.set_default_mediator_by_id.assert_called_once()

    async def test_set_default_mediator_x(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"mediation.default_id": "test-id"})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        with (
            mock.patch.object(
                MediationRecord,
                "retrieve_by_id",
                mock.CoroutineMock(side_effect=Exception()),
            ),
            mock.patch.object(test_module, "LOGGER") as mock_logger,
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
        with mock.patch.object(
            conductor.outbound_transport_manager, "enqueue_webhook"
        ) as mock_enqueue:
            conductor.webhook_router(
                test_topic, test_payload, test_endpoint, test_attempts
            )
            mock_enqueue.assert_called_once_with(
                test_topic, test_payload, test_endpoint, test_attempts, None
            )

        # swallow error
        with mock.patch.object(
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

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            multitenant_mgr = conductor.context.inject(BaseMultitenantManager)
            assert isinstance(multitenant_mgr, MultitenantManager)

            multitenant_mgr._profiles.put(
                "test1",
                mock.MagicMock(close=mock.CoroutineMock()),
            )
            multitenant_mgr._profiles.put(
                "test2",
                mock.MagicMock(close=mock.CoroutineMock()),
            )

            await conductor.stop()

            multitenant_mgr._profiles.profiles["test1"].close.assert_called_once_with()
            multitenant_mgr._profiles.profiles["test2"].close.assert_called_once_with()


def get_invite_store_mock(
    invite_string: str, invite_already_used: bool = False
) -> mock.MagicMock:
    unused_invite = MediationInviteRecord(invite_string, invite_already_used)
    used_invite = MediationInviteRecord(invite_string, used=True)

    return mock.MagicMock(
        get_mediation_invite_record=mock.CoroutineMock(return_value=unused_invite),
        mark_default_invite_as_used=mock.CoroutineMock(return_value=used_invite),
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

    @mock.patch.object(
        test_module,
        "MediationInviteStore",
        return_value=get_invite_store_mock("test-invite"),
    )
    @mock.patch.object(test_module.InvitationMessage, "from_url")
    async def test_mediator_invitation_0434(self, mock_from_url, _):
        builder = self.__get_mediator_config("test-invite", True)
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
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

        with (
            mock.patch.object(
                test_module,
                "OutOfBandManager",
                mock.MagicMock(
                    return_value=mock.MagicMock(
                        receive_invitation=mock.CoroutineMock(return_value=oob_record)
                    )
                ),
            ) as mock_mgr,
            mock.patch.object(
                test_module,
                "upgrade_wallet_to_anoncreds_if_requested",
                return_value=False,
            ),
        ):
            assert not conductor.root_profile.settings["mediation.connections_invite"]
            await conductor.start()
            await conductor.stop()
            mock_from_url.assert_called_once_with("test-invite")
            mock_mgr.return_value.receive_invitation.assert_called_once()

    @mock.patch.object(test_module, "MediationInviteStore")
    @mock.patch.object(test_module, "BaseConnectionManager")
    async def test_mediation_invitation_should_not_create_connection_for_old_invitation(
        self, patched_connection_manager, patched_invite_store
    ):
        # given
        invite_string = "test-invite"

        builder = self.__get_mediator_config("test-invite", True)
        conductor = test_module.Conductor(builder)
        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

        invite_store_mock = get_invite_store_mock(invite_string, True)
        patched_invite_store.return_value = invite_store_mock

        connection_manager_mock = mock.MagicMock(receive_invitation=mock.CoroutineMock())
        patched_connection_manager.return_value = connection_manager_mock
        # when
        await conductor.start()
        await conductor.stop()

        # then
        invite_store_mock.get_mediation_invite_record.assert_called_with(invite_string)
        connection_manager_mock.receive_invitation.assert_not_called()

    async def test_setup_ledger_both_multiple_and_base(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"ledger.genesis_transactions": "..."})
        builder.update_settings(
            {
                "ledger.ledger_config_list": [
                    {
                        "id": "sovrinMain",
                        "is_production": True,
                        "is_write": True,
                    },
                ]
            }
        )
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())
        test_profile.context.injector.bind_instance(
            BaseLedger, mock.MagicMock(BaseLedger, autospec=True)
        )

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module,
                "load_multiple_genesis_transactions_from_config",
                mock.CoroutineMock(),
            ) as mock_multiple_genesis_load,
            mock.patch.object(
                test_module, "get_genesis_transactions", mock.CoroutineMock()
            ) as mock_genesis_load,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(test_module, "ledger_config"),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_multiple_genesis_load.assert_called_once()
            mock_genesis_load.assert_called_once()

    async def test_setup_ledger_only_base(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        builder.update_settings({"ledger.genesis_transactions": "..."})
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "get_genesis_transactions", mock.CoroutineMock()
            ) as mock_genesis_load,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(test_module, "ledger_config"),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()
            mock_genesis_load.assert_called_once()

    async def test_startup_storage_type_anoncreds_and_config_askar_re_calls_setup(self):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module,
                "upgrade",
                mock.CoroutineMock(),
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }

            async with test_profile.session() as session:
                storage = session.inject(BaseStorage)
                await storage.add_record(
                    StorageRecord(RECORD_TYPE_ACAPY_STORAGE_TYPE, "askar-anoncreds")
                )

            await conductor.setup()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}
            with mock.patch.object(test_module.Conductor, "setup") as mock_setup:
                mock_setup.return_value = None
                with self.assertRaises(Exception):
                    await conductor.start()
                assert mock_setup.called

            # await conductor.stop()

    async def test_startup_storage_type_does_not_exist_and_existing_agent_then_set_to_askar(
        self,
    ):
        builder: ContextBuilder = StubContextBuilder(self.test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(None, await builder.build_context())

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(
                    return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
                ),
            ),
            mock.patch.object(
                test_module,
                "upgrade",
                mock.CoroutineMock(),
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}

            await conductor.start()

            async with test_profile.session() as session:
                storage = session.inject(BaseStorage)
                record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
                )
                assert record.value == "askar"

            await conductor.stop()

    async def test_startup_storage_type_does_not_exist_and_new_anoncreds_agent(
        self,
    ):
        test_settings = {
            "admin.webhook_urls": ["http://sample.webhook.ca"],
            "wallet.type": "askar-anoncreds",
        }
        builder: ContextBuilder = StubContextBuilder(test_settings)
        conductor = test_module.Conductor(builder)

        test_profile = await create_test_profile(
            test_settings, await builder.build_context()
        )

        with (
            mock.patch.object(
                test_module,
                "wallet_config",
                return_value=(
                    test_profile,
                    DIDInfo("did", "verkey", metadata={}, method=SOV, key_type=ED25519),
                ),
            ),
            mock.patch.object(
                test_module, "InboundTransportManager", autospec=True
            ) as mock_inbound_mgr,
            mock.patch.object(
                test_module, "OutboundTransportManager", autospec=True
            ) as mock_outbound_mgr,
            mock.patch.object(
                test_module,
                "get_upgrade_version_list",
                mock.MagicMock(
                    return_value=["v0.7.4", "0.7.5", "v0.8.0-rc1", "v8.0.0", "v0.8.1-rc2"]
                ),
            ),
            mock.patch.object(
                test_module,
                "upgrade",
                mock.CoroutineMock(),
            ),
        ):
            mock_outbound_mgr.return_value.registered_transports = {
                "test": mock.MagicMock(schemes=["http"])
            }
            await conductor.setup()

            mock_inbound_mgr.return_value.registered_transports = {}
            mock_outbound_mgr.return_value.registered_transports = {}

            await conductor.start()
            async with test_profile.session() as session:
                storage = session.inject(BaseStorage)
                record = await storage.find_record(
                    type_filter=RECORD_TYPE_ACAPY_STORAGE_TYPE, tag_query={}
                )
                assert record.value == "askar-anoncreds"

            await conductor.stop()
