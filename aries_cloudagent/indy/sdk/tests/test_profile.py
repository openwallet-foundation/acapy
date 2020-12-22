import pytest

from ....config.injection_context import InjectionContext
from ..profile import IndySdkProfile
from ..wallet_setup import IndyWalletConfig, IndyOpenWallet
from ....ledger.indy import IndySdkLedgerPool
from ....config.injection_context import InjectionContext


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
