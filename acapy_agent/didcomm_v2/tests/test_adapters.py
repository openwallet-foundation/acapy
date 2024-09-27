from unittest import IsolatedAsyncioTestCase

from acapy_agent.askar.profile import AskarProfile, AskarProfileSession
from acapy_agent.config.injection_context import InjectionContext
from acapy_agent.core.event_bus import EventBus
from acapy_agent.core.in_memory.profile import InMemoryProfile
from acapy_agent.core.profile import Profile
from acapy_agent.core.protocol_registry import ProtocolRegistry
from acapy_agent.protocols.coordinate_mediation.v1_0.route_manager import (
    RouteManager,
)
from acapy_agent.resolver.base import BaseDIDResolver
from acapy_agent.resolver.did_resolver import DIDResolver
from acapy_agent.tests.mock import AsyncMock, MagicMock
from acapy_agent.utils.stats import Collector

from ..adapters import ResolverAdapter, SecretsAdapter, SecretsAdapterError


def make_profile() -> Profile:
    profile = InMemoryProfile.test_profile(settings={"experiment.didcommv2": True})
    profile.context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
    profile.context.injector.bind_instance(Collector, Collector())
    profile.context.injector.bind_instance(EventBus, EventBus())
    profile.context.injector.bind_instance(RouteManager, MagicMock())
    return profile


class TestDIDResolver(BaseDIDResolver):
    async def setup(self, context: InjectionContext):
        return await super().setup(context)

    async def _resolve(self, profile, did):
        return await self.resolve(profile, did)

    async def resolve(
        self,
        profile,
        did,
        sercive_accept=None,
    ):
        return {"did": did, "test": "didDoc"}

    async def supports(self, profile, did: str):
        if did.startswith("did:test"):
            return True
        return False


class TestAdapters(IsolatedAsyncioTestCase):
    test_did = "did:test:0"
    invalid_did = "this shouldn't work"
    profile = make_profile()
    resolver = DIDResolver()
    resolver.register_resolver(TestDIDResolver())
    res_adapter = ResolverAdapter(profile=profile, resolver=resolver)

    async def test_resolver_adapter_resolve_did(self):
        doc = await self.res_adapter.resolve(self.test_did)
        assert doc["did"] == self.test_did

    async def test_resolver_adapter_is_resolvable(self):
        valid = await self.res_adapter.is_resolvable(self.test_did)
        assert valid

        invalid = await self.res_adapter.is_resolvable(self.invalid_did)
        assert not invalid

    async def test_secrets_adapter_errors(self):
        sec_adapter = SecretsAdapter(session=MagicMock())
        with self.assertRaises(SecretsAdapterError) as ctx:
            await sec_adapter.get_secret_by_kid("kid")

        assert "ACA-Py's implementation of DMP only supports an Askar backend" in str(
            ctx.exception
        )

        store = MagicMock()
        askar_profile = AskarProfile(opened=store)
        session: AskarProfileSession = askar_profile.session()
        sec_adapter = SecretsAdapter(session)

        session._handle = MagicMock()
        session._handle.fetch_all_keys = AsyncMock(return_value=["key1", "key2"])

        with self.assertRaises(SecretsAdapterError) as ctx:
            await sec_adapter.get_secret_by_kid("kid")

        assert "More than one key found with kid" in str(ctx.exception)

    async def test_secrets_adapter_empty(self):
        store = MagicMock()
        askar_profile = AskarProfile(opened=store)
        session: AskarProfileSession = askar_profile.session()
        sec_adapter = SecretsAdapter(session)

        session._handle = MagicMock()
        session._handle.fetch_all_keys = AsyncMock(return_value=[None])

        assert not await sec_adapter.get_secret_by_kid("kid")

    async def test_secrets_adapter_valid_return(self):
        store = MagicMock()
        askar_profile = AskarProfile(opened=store)
        session: AskarProfileSession = askar_profile.session()
        sec_adapter = SecretsAdapter(session)

        entry = MagicMock()
        entry.key = "key1"

        session._handle = MagicMock()
        session._handle.fetch_all_keys = AsyncMock(return_value=[entry])

        key = await sec_adapter.get_secret_by_kid("kid")

        assert key.key == "key1"
