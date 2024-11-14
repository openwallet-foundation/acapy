from unittest import IsolatedAsyncioTestCase

from ...askar.profile import AskarProfile, AskarProfileSession
from ...config.injection_context import InjectionContext
from ...core.event_bus import EventBus
from ...core.protocol_registry import ProtocolRegistry
from ...protocols.coordinate_mediation.v1_0.route_manager import (
    RouteManager,
)
from ...resolver.base import BaseDIDResolver
from ...resolver.did_resolver import DIDResolver
from ...tests.mock import AsyncMock, MagicMock
from ...utils.stats import Collector
from ...utils.testing import create_test_profile
from ..adapters import ResolverAdapter, SecretsAdapter, SecretsAdapterError


class MockDIDResolver(BaseDIDResolver):
    async def setup(self, context: InjectionContext):
        return await super().setup(context)

    async def _resolve(self, profile, did):
        return await self.resolve(profile, did)

    async def resolve(
        self,
        profile,
        did,
        service_accept=None,
    ):
        return {"did": did, "test": "didDoc"}

    async def supports(self, profile, did: str):
        if did.startswith("did:test"):
            return True
        return False


class TestAdapters(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile(settings={"experiment.didcommv2": True})
        self.profile.context.injector.bind_instance(ProtocolRegistry, ProtocolRegistry())
        self.profile.context.injector.bind_instance(Collector, Collector())
        self.profile.context.injector.bind_instance(EventBus, EventBus())
        self.profile.context.injector.bind_instance(RouteManager, MagicMock())
        self.test_did = "did:test:0"
        self.invalid_did = "this shouldn't work"
        resolver = DIDResolver()
        resolver.register_resolver(MockDIDResolver())
        self.res_adapter = ResolverAdapter(profile=self.profile, resolver=resolver)

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
