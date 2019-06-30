"""Classes for configuring the default injection context."""

from .base import ConfigError
from .base_context import ContextBuilder
from .injection_context import InjectionContext
from .provider import CachedProvider, ClassProvider, StatsProvider

from ..cache.base import BaseCache
from ..cache.basic import BasicCache
from ..classloader import ClassLoader
from ..defaults import default_protocol_registry
from ..ledger.base import BaseLedger
from ..ledger.provider import LedgerProvider
from ..issuer.base import BaseIssuer
from ..holder.base import BaseHolder
from ..verifier.base import BaseVerifier
from ..messaging.actionmenu.base_service import BaseMenuService
from ..messaging.actionmenu.driver_service import DriverMenuService
from ..messaging.introduction.base_service import BaseIntroductionService
from ..messaging.introduction.demo_service import DemoIntroductionService
from ..messaging.protocol_registry import ProtocolRegistry
from ..messaging.serializer import MessageSerializer
from ..stats import Collector
from ..storage.base import BaseStorage
from ..storage.provider import StorageProvider
from ..transport.outbound.queue.base import BaseOutboundMessageQueue
from ..wallet.base import BaseWallet
from ..wallet.provider import WalletProvider


class DefaultContextBuilder(ContextBuilder):
    """Default context builder."""

    async def build(self) -> InjectionContext:
        """Build the new injection context."""
        context = InjectionContext(settings=self.settings)
        context.settings.set_default("default_label", "Aries Cloud Agent")

        if context.settings.get("timing.enabled"):
            collector = Collector()
            context.injector.bind_instance(Collector, collector)

        context.injector.bind_instance(BaseCache, BasicCache())

        await self.bind_providers(context)

        return context

    async def bind_providers(self, context: InjectionContext):
        """Bind various class providers."""

        context.injector.bind_provider(
            BaseStorage,
            CachedProvider(
                StatsProvider(
                    StorageProvider(), ("add_record", "get_record", "search_records")
                )
            ),
        )
        context.injector.bind_provider(
            BaseWallet,
            CachedProvider(
                StatsProvider(
                    WalletProvider(),
                    (
                        "create",
                        "open",
                        "sign_message",
                        "verify_message",
                        "encrypt_message",
                        "decrypt_message",
                        "pack_message",
                        "unpack_message",
                        "get_local_did",
                    ),
                )
            ),
        )

        context.injector.bind_provider(
            BaseLedger,
            CachedProvider(
                StatsProvider(
                    LedgerProvider(),
                    (
                        "get_credential_definition",
                        "get_schema",
                        "send_credential_definition",
                        "send_schema",
                    ),
                )
            ),
        )
        context.injector.bind_provider(
            BaseIssuer,
            StatsProvider(
                ClassProvider(
                    "aries_cloudagent.issuer.indy.IndyIssuer",
                    ClassProvider.Inject(BaseWallet),
                ),
                ("create_credential_offer", "create_credential"),
            ),
        )
        context.injector.bind_provider(
            BaseHolder,
            StatsProvider(
                ClassProvider(
                    "aries_cloudagent.holder.indy.IndyHolder",
                    ClassProvider.Inject(BaseWallet),
                ),
                ("get_credential", "store_credential", "create_credential_request"),
            ),
        )
        context.injector.bind_provider(
            BaseVerifier,
            ClassProvider(
                "aries_cloudagent.verifier.indy.IndyVerifier",
                ClassProvider.Inject(BaseWallet),
            ),
        )

        # Set up protocol registry
        protocol_registry: ProtocolRegistry = default_protocol_registry()
        # Dynamically register externally loaded protocol message types
        for protocol_module_path in self.settings.get("external_protocols", []):
            try:
                external_module = ClassLoader.load_module(
                    f"{protocol_module_path}.message_types"
                )
                protocol_registry.register_message_types(external_module.MESSAGE_TYPES)
            except Exception as e:
                raise ConfigError(
                    "Failed to load external protocol module "
                    + f"'{protocol_module_path}'"
                ) from e
        context.injector.bind_instance(ProtocolRegistry, protocol_registry)

        # Register message serializer
        context.injector.bind_provider(
            MessageSerializer,
            CachedProvider(
                StatsProvider(
                    ClassProvider(MessageSerializer),
                    ("encode_message", "parse_message"),
                )
            ),
        )

        # Set default outbound message queue
        context.injector.bind_provider(
            BaseOutboundMessageQueue,
            ClassProvider(
                "aries_cloudagent.transport.outbound.queue"
                + ".basic.BasicOutboundMessageQueue"
            ),
        )

        # Allow action menu to be provided by driver
        context.injector.bind_instance(BaseMenuService, DriverMenuService(context))
        context.injector.bind_instance(
            BaseIntroductionService, DemoIntroductionService(context)
        )
