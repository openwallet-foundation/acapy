import pytest

from aries_cloudagent.tests import mock

from ....config.injection_context import InjectionContext
from ....core.error import ProfileError
from ....ledger.base import BaseLedger
from ....ledger.indy import IndySdkLedgerPool

from ..profile import IndySdkProfile
from ..wallet_setup import IndyOpenWallet, IndyWalletConfig

from .. import profile as test_module


@pytest.fixture
async def open_wallet():
    opened = IndyOpenWallet(
        config=IndyWalletConfig({"name": "test-profile"}),
        created=True,
        handle=1,
        master_secret_id="master-secret",
    )
    with mock.patch.object(opened, "close", mock.CoroutineMock()):
        yield opened


@pytest.fixture()
async def profile(open_wallet):
    context = InjectionContext()
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    profile = IndySdkProfile(open_wallet, context)

    yield profile

    # Trigger finalizer before event loop fixture is closed
    profile._finalizer()


@pytest.mark.asyncio
async def test_init_multi_ledger(open_wallet):
    context = InjectionContext(
        settings={
            "ledger.ledger_config_list": [
                {
                    "id": "BCovrinDev",
                    "is_production": True,
                    "is_write": True,
                    "endorser_did": "9QPa6tHvBHttLg6U4xvviv",
                    "endorser_alias": "endorser_dev",
                    "genesis_transactions": mock.MagicMock(),
                },
                {
                    "id": "SovrinStagingNet",
                    "is_production": False,
                    "genesis_transactions": mock.MagicMock(),
                },
            ]
        }
    )
    askar_profile = IndySdkProfile(
        open_wallet,
        context=context,
    )

    assert askar_profile.opened == open_wallet
    assert askar_profile.settings["endorser.endorser_alias"] == "endorser_dev"
    assert (
        askar_profile.settings["endorser.endorser_public_did"]
        == "9QPa6tHvBHttLg6U4xvviv"
    )
    assert (askar_profile.inject_or(BaseLedger)).pool_name == "BCovrinDev"


@pytest.mark.asyncio
async def test_properties(profile: IndySdkProfile):
    assert profile.name == "test-profile"
    assert profile.backend == "indy"
    assert profile.wallet and profile.wallet.handle == 1

    assert "IndySdkProfile" in str(profile)
    assert profile.created
    assert profile.wallet.created
    assert profile.wallet.master_secret_id == "master-secret"

    with mock.patch.object(profile, "opened", False):
        with pytest.raises(ProfileError):
            await profile.remove()

    with mock.patch.object(profile.opened, "close", mock.CoroutineMock()):
        await profile.remove()
        assert profile.opened is None


def test_settings_genesis_transactions(open_wallet):
    context = InjectionContext(
        settings={"ledger.genesis_transactions": mock.MagicMock()}
    )
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    profile = IndySdkProfile(open_wallet, context)


def test_settings_ledger_config(open_wallet):
    context = InjectionContext(
        settings={
            "ledger.ledger_config_list": [
                mock.MagicMock(),
                mock.MagicMock(),
            ]
        }
    )
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    profile = IndySdkProfile(open_wallet, context)


def test_read_only(open_wallet):
    context = InjectionContext(settings={"ledger.read_only": True})
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    ro_profile = IndySdkProfile(open_wallet, context)


def test_finalizer(open_wallet):
    profile = IndySdkProfile(open_wallet)
    assert profile
    with mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger:
        profile._finalizer()
        assert mock_logger.debug.call_count == 1
        mock_logger.debug.assert_called_once_with(
            "Profile finalizer called; closing wallet"
        )
