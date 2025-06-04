from tempfile import NamedTemporaryFile
from unittest import IsolatedAsyncioTestCase

from ...cache.base import BaseCache
from ...core.plugin_registry import PluginRegistry
from ...core.profile import ProfileManager
from ...core.protocol_registry import ProtocolRegistry
from ...transport.wire_format import BaseWireFormat
from ..default_context import DefaultContextBuilder
from ..injection_context import InjectionContext


class TestDefaultContext(IsolatedAsyncioTestCase):
    async def test_build_context(self):
        """Test context init."""

        builder = DefaultContextBuilder()
        result = await builder.build_context()
        assert isinstance(result, InjectionContext)

        for cls in (
            BaseCache,
            BaseWireFormat,
            ProfileManager,
            ProtocolRegistry,
        ):
            assert isinstance(result.inject(cls), cls)

        builder = DefaultContextBuilder(
            settings={
                "timing.enabled": True,
                "timing.log.file": NamedTemporaryFile().name,
                "multitenant.enabled": True,
                "multitenant.admin_enabled": True,
            }
        )
        result = await builder.build_context()
        assert isinstance(result, InjectionContext)

    async def test_plugin_registration_askar_anoncreds(self):
        """Test anoncreds plugins are registered when wallet_type is askar-anoncreds."""
        builder = DefaultContextBuilder(
            settings={
                "wallet.type": "askar-anoncreds",
            }
        )
        result = await builder.build_context()
        plugin_registry = result.inject(PluginRegistry)

        # Check that anoncreds plugins are registered
        for plugin in [
            "acapy_agent.anoncreds",
            "acapy_agent.anoncreds.default.did_web",
            "acapy_agent.anoncreds.default.legacy_indy",
            "acapy_agent.revocation_anoncreds",
        ]:
            assert plugin in plugin_registry.plugin_names

    async def test_plugin_registration_multitenant_enabled(self):
        """Test anoncreds plugins are registered when multitenant is enabled."""
        builder = DefaultContextBuilder(
            settings={
                "multitenant.enabled": True,
            }
        )
        result = await builder.build_context()
        plugin_registry = result.inject(PluginRegistry)

        # Check that anoncreds and askar plugins are registered
        for plugin in [
            "acapy_agent.anoncreds",
            "acapy_agent.anoncreds.default.did_web",
            "acapy_agent.anoncreds.default.legacy_indy",
            "acapy_agent.revocation_anoncreds",
            "acapy_agent.messaging.credential_definitions",
            "acapy_agent.messaging.schemas",
            "acapy_agent.revocation",
        ]:
            assert plugin in plugin_registry.plugin_names

    async def test_plugin_registration_askar_only(self):
        """Test only askar plugins are registered when wallet_type is askar and multitenant is not enabled."""
        builder = DefaultContextBuilder(
            settings={
                "wallet.type": "askar",
                "multitenant.enabled": False,
            }
        )
        result = await builder.build_context()
        plugin_registry = result.inject(PluginRegistry)

        # Check that only askar plugins are registered
        for plugin in [
            "acapy_agent.messaging.credential_definitions",
            "acapy_agent.messaging.schemas",
            "acapy_agent.revocation",
        ]:
            assert plugin in plugin_registry.plugin_names

        # Ensure anoncreds plugins are not registered
        for plugin in [
            "acapy_agent.anoncreds",
            "acapy_agent.anoncreds.default.did_web",
            "acapy_agent.anoncreds.default.legacy_indy",
            "acapy_agent.revocation_anoncreds",
        ]:
            assert plugin not in plugin_registry.plugin_names
