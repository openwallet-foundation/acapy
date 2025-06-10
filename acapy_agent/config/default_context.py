"""Classes for configuring the default injection context."""

import logging

from ..anoncreds.registry import AnonCredsRegistry
from ..cache.base import BaseCache
from ..cache.in_memory import InMemoryCache
from ..connections.base_manager import BaseConnectionManager
from ..core.event_bus import EventBus
from ..core.goal_code_registry import GoalCodeRegistry
from ..core.plugin_registry import PluginRegistry
from ..core.profile import Profile, ProfileManager, ProfileManagerProvider
from ..core.protocol_registry import ProtocolRegistry
from ..protocols.actionmenu.v1_0.base_service import BaseMenuService
from ..protocols.actionmenu.v1_0.driver_service import DriverMenuService
from ..protocols.introduction.v0_1.base_service import BaseIntroductionService
from ..protocols.introduction.v0_1.demo_service import DemoIntroductionService
from ..resolver.did_resolver import DIDResolver
from ..transport.wire_format import BaseWireFormat
from ..utils.stats import Collector
from ..wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ..wallet.did_method import DIDMethods
from ..wallet.key_type import KeyTypes
from .base_context import ContextBuilder
from .injection_context import InjectionContext
from .provider import CachedProvider, ClassProvider

LOGGER = logging.getLogger(__name__)


class DefaultContextBuilder(ContextBuilder):
    """Default context builder."""

    async def build_context(self) -> InjectionContext:
        """Build the base injection context; set DIDComm prefix to emit."""
        LOGGER.debug("Building new injection context")

        context = InjectionContext(settings=self.settings)
        context.settings.set_default("default_label", "Aries Cloud Agent")

        if context.settings.get("timing.enabled"):
            timing_log = context.settings.get("timing.log_file")
            LOGGER.debug("Enabling timing collector with log file: %s", timing_log)
            collector = Collector(log_path=timing_log)
            context.injector.bind_instance(Collector, collector)

        # Shared in-memory cache
        context.injector.bind_instance(BaseCache, InMemoryCache())

        # Global protocol registry
        context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())

        # Global goal code registry
        context.injector.bind_instance(GoalCodeRegistry, GoalCodeRegistry())

        # Global event bus
        context.injector.bind_instance(EventBus, EventBus())

        # Global did resolver
        context.injector.bind_instance(DIDResolver, DIDResolver())
        context.injector.bind_instance(AnonCredsRegistry, AnonCredsRegistry())
        context.injector.bind_instance(DIDMethods, DIDMethods())
        context.injector.bind_instance(KeyTypes, KeyTypes())
        context.injector.bind_instance(
            BaseVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )

        # DIDComm Messaging
        if context.settings.get("experiment.didcomm_v2"):
            LOGGER.info("DIDComm v2 experimental mode enabled")
            from didcomm_messaging import CryptoService, PackagingService, RoutingService
            from didcomm_messaging.crypto.backend.askar import AskarCryptoService

            context.injector.bind_instance(CryptoService, AskarCryptoService())
            context.injector.bind_instance(PackagingService, PackagingService())
            context.injector.bind_instance(RoutingService, RoutingService())

        await self.bind_providers(context)
        await self.load_plugins(context)

        return context

    async def bind_providers(self, context: InjectionContext):
        """Bind various class providers."""
        LOGGER.debug("Begin binding providers to context")

        context.injector.bind_provider(ProfileManager, ProfileManagerProvider())

        # Register default pack format
        context.injector.bind_provider(
            BaseWireFormat,
            CachedProvider(
                ClassProvider("acapy_agent.transport.pack_format.PackWireFormat"),
            ),
        )

        # Allow action menu to be provided by driver
        context.injector.bind_instance(BaseMenuService, DriverMenuService(context))
        context.injector.bind_instance(BaseIntroductionService, DemoIntroductionService())

        # Allow BaseConnectionManager to be overridden
        context.injector.bind_provider(
            BaseConnectionManager,
            ClassProvider(BaseConnectionManager, ClassProvider.Inject(Profile)),
        )

    async def load_plugins(self, context: InjectionContext):
        """Set up plugin registry and load plugins."""

        LOGGER.debug("Initializing plugin registry")
        plugin_registry = PluginRegistry(
            blocklist=self.settings.get("blocked_plugins", [])
        )
        context.injector.bind_instance(PluginRegistry, plugin_registry)

        # Register standard protocol plugins
        if not self.settings.get("transport.disabled"):
            plugin_registry.register_package("acapy_agent.protocols")

        # Define core plugins
        core_plugins = [
            "acapy_agent.holder",
            "acapy_agent.ledger",
            "acapy_agent.connections",
            "acapy_agent.messaging.jsonld",
            "acapy_agent.resolver",
            "acapy_agent.settings",
            "acapy_agent.vc",
            "acapy_agent.vc.data_integrity",
            "acapy_agent.wallet",
            "acapy_agent.wallet.keys",
        ]

        did_management_plugins = [
            "acapy_agent.did.indy",
        ]

        default_plugins = core_plugins + did_management_plugins

        LOGGER.info("Registering default plugins")
        for plugin in default_plugins:
            plugin_registry.register_plugin(plugin)

        anoncreds_plugins = [
            "acapy_agent.anoncreds",
            "acapy_agent.anoncreds.default.did_web",
            "acapy_agent.anoncreds.default.legacy_indy",
            "acapy_agent.revocation_anoncreds",
        ]

        askar_plugins = [
            "acapy_agent.messaging.credential_definitions",
            "acapy_agent.messaging.schemas",
            "acapy_agent.revocation",
        ]

        def register_askar_plugins():
            LOGGER.info("Registering askar plugins")
            for plugin in askar_plugins:
                plugin_registry.register_plugin(plugin)

        def register_anoncreds_plugins():
            LOGGER.info("Registering anoncreds plugins")
            for plugin in anoncreds_plugins:
                plugin_registry.register_plugin(plugin)

        if context.settings.get("multitenant.enabled"):
            # Register both askar and anoncreds plugins for multitenancy
            register_askar_plugins()
            register_anoncreds_plugins()
        elif self.settings.get("wallet.type") == "askar-anoncreds":
            register_anoncreds_plugins()
        else:
            register_askar_plugins()

        if context.settings.get("multitenant.admin_enabled"):
            LOGGER.info("Registering multitenant admin API plugin")
            plugin_registry.register_plugin("acapy_agent.multitenant.admin")

        # Register external plugins
        for plugin_path in self.settings.get("external_plugins", []):
            LOGGER.debug("Registering external plugin: %s", plugin_path)
            plugin_registry.register_plugin(plugin_path)

        # Register message protocols
        await plugin_registry.init_context(context)
