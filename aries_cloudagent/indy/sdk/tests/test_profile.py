import asyncio
import logging

from asynctest import mock as async_mock
import pytest

from ....config.injection_context import InjectionContext
from ....core.error import ProfileError
from ....ledger.indy import IndySdkLedgerPool
from ..profile import IndySdkProfile
from ..wallet_setup import IndyOpenWallet, IndyWalletConfig


@pytest.fixture
async def open_wallet():
    opened = IndyOpenWallet(
        config=IndyWalletConfig({"name": "test-profile"}),
        created=True,
        handle=1,
        master_secret_id="master-secret",
    )
    with async_mock.patch.object(opened, "close", async_mock.CoroutineMock()):
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
async def test_properties(profile: IndySdkProfile):
    assert profile.name == "test-profile"
    assert profile.backend == "indy"
    assert profile.wallet and profile.wallet.handle == 1

    assert "IndySdkProfile" in str(profile)
    assert profile.created
    assert profile.wallet.created
    assert profile.wallet.master_secret_id == "master-secret"

    with async_mock.patch.object(profile, "opened", False):
        with pytest.raises(ProfileError):
            await profile.remove()

    with async_mock.patch.object(profile.opened, "close", async_mock.CoroutineMock()):
        await profile.remove()
        assert profile.opened is None


def test_settings_genesis_transactions(open_wallet):
    context = InjectionContext(
        settings={"ledger.genesis_transactions": async_mock.MagicMock()}
    )
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    profile = IndySdkProfile(open_wallet, context)


def test_settings_ledger_config(open_wallet):
    context = InjectionContext(settings={"ledger.ledger_config_list": True})
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    profile = IndySdkProfile(open_wallet, context)


def test_read_only(open_wallet):
    context = InjectionContext(settings={"ledger.read_only": True})
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    ro_profile = IndySdkProfile(open_wallet, context)


def test_finalizer(open_wallet, caplog):
    def _smaller_scope():
        profile = IndySdkProfile(open_wallet)
        assert profile

    with caplog.at_level(logging.DEBUG):
        _smaller_scope()

    assert "finalizer called" in caplog.text
