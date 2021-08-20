import asyncio

from asynctest import TestCase as AsyncTestCase, mock

from aries_cloudagent.askar.profile import AskarProfile
from aries_cloudagent.config.injection_context import InjectionContext

class TestProfile(AsyncTestCase):
    @mock.patch("aries_cloudagent.askar.store.AskarOpenStore")
    async def test_init_success(self, AskarOpenStore):
        askar_profile = AskarProfile(
            AskarOpenStore,
        )

        assert askar_profile.opened == AskarOpenStore

    @mock.patch("aries_cloudagent.askar.store.AskarOpenStore")
    async def test_remove_success(self, AskarOpenStore):
        openStore = AskarOpenStore
        context = InjectionContext() 
        context.settings = {
            "multitenant.wallet_type": "askar-profile"
        }
        askar_profile = AskarProfile(
            openStore,
            context
        )
        remove_profile_stub = asyncio.Future()
        remove_profile_stub.set_result(True)
        openStore.store.remove_profile.return_value = remove_profile_stub

        await askar_profile.remove()
        
        openStore.store.remove_profile.assert_called_once()

    @mock.patch("aries_cloudagent.askar.store.AskarOpenStore")
    async def test_remove_profile_not_removed_if_wallet_type_not_askar_profile(self, AskarOpenStore):
        openStore = AskarOpenStore
        context = InjectionContext() 
        context.settings = {
            "multitenant.wallet_type": "basic"
        }
        askar_profile = AskarProfile(
            openStore,
            context
        )
        
        await askar_profile.remove()
        
        openStore.store.remove_profile.assert_not_called()
