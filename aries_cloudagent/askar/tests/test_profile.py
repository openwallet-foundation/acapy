import asyncio
import logging
import pytest

from asynctest import mock

from ...askar.profile import AskarProfile
from ...config.injection_context import InjectionContext

from .. import profile as test_module


@pytest.fixture
def open_store():
    yield mock.MagicMock()


@pytest.mark.asyncio
async def test_init_success(open_store):
    askar_profile = AskarProfile(
        open_store,
    )

    assert askar_profile.opened == open_store


@pytest.mark.asyncio
async def test_remove_success(open_store):
    openStore = open_store
    context = InjectionContext()
    profile_id = "profile_id"
    context.settings = {
        "multitenant.wallet_type": "askar-profile",
        "wallet.askar_profile": profile_id,
        "ledger.genesis_transactions": mock.MagicMock(),
    }
    askar_profile = AskarProfile(openStore, context, profile_id=profile_id)
    remove_profile_stub = asyncio.Future()
    remove_profile_stub.set_result(True)
    openStore.store.remove_profile.return_value = remove_profile_stub

    await askar_profile.remove()

    openStore.store.remove_profile.assert_called_once_with(profile_id)


@pytest.mark.asyncio
async def test_remove_profile_not_removed_if_wallet_type_not_askar_profile(open_store):
    openStore = open_store
    context = InjectionContext()
    context.settings = {"multitenant.wallet_type": "basic"}
    askar_profile = AskarProfile(openStore, context)

    await askar_profile.remove()

    openStore.store.remove_profile.assert_not_called()


@pytest.mark.asyncio
async def test_profile_manager_transaction():
    profile = "profileId"

    with mock.patch("aries_cloudagent.askar.profile.AskarProfile") as AskarProfile:
        askar_profile = AskarProfile(None, True, profile_id=profile)
        askar_profile.profile_id = profile
        askar_profile_transaction = mock.MagicMock()
        askar_profile.store.transaction.return_value = askar_profile_transaction

        transactionProfile = test_module.AskarProfileSession(askar_profile, True)

        assert transactionProfile._opener == askar_profile_transaction
        askar_profile.store.transaction.assert_called_once_with(profile)


@pytest.mark.asyncio
async def test_profile_manager_store():
    profile = "profileId"

    with mock.patch("aries_cloudagent.askar.profile.AskarProfile") as AskarProfile:
        askar_profile = AskarProfile(None, False, profile_id=profile)
        askar_profile.profile_id = profile
        askar_profile_session = mock.MagicMock()
        askar_profile.store.session.return_value = askar_profile_session

        sessionProfile = test_module.AskarProfileSession(askar_profile, False)

        assert sessionProfile._opener == askar_profile_session
        askar_profile.store.session.assert_called_once_with(profile)
