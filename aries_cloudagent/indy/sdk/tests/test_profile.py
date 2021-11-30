import pytest

from asynctest import mock as async_mock

from ....config.injection_context import InjectionContext
from ....core.error import ProfileError
from ....ledger.indy import IndySdkLedgerPool

from ..profile import IndySdkProfile
from ..wallet_setup import IndyWalletConfig, IndyOpenWallet


@pytest.fixture()
async def profile():
    context = InjectionContext()
    context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
    yield IndySdkProfile(
        IndyOpenWallet(
            config=IndyWalletConfig({"name": "test-profile"}),
            created=True,
            handle=1,
            master_secret_id="master-secret",
        ),
        context,
    )


class TestIndySdkProfile:
    @pytest.mark.asyncio
    async def test_properties(self, profile):
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

        with async_mock.patch.object(
            profile.opened, "close", async_mock.CoroutineMock()
        ):
            await profile.remove()
            assert profile.opened is None

    def test_settings_genesis_transactions(self):
        context = InjectionContext(
            settings={"ledger.genesis_transactions": async_mock.MagicMock()}
        )
        context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
        profile = IndySdkProfile(
            IndyOpenWallet(
                config=IndyWalletConfig({"name": "test-profile"}),
                created=True,
                handle=1,
                master_secret_id="master-secret",
            ),
            context,
        )

    def test_settings_ledger_config(self):
        context = InjectionContext(settings={"ledger.ledger_config_list": True})
        context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
        profile = IndySdkProfile(
            IndyOpenWallet(
                config=IndyWalletConfig({"name": "test-profile"}),
                created=True,
                handle=1,
                master_secret_id="master-secret",
            ),
            context,
        )

    def test_read_only(self):
        context = InjectionContext(settings={"ledger.read_only": True})
        context.injector.bind_instance(IndySdkLedgerPool, IndySdkLedgerPool("name"))
        ro_profile = IndySdkProfile(
            IndyOpenWallet(
                config=IndyWalletConfig({"name": "test-profile"}),
                created=True,
                handle=1,
                master_secret_id="master-secret",
            ),
            context,
        )
