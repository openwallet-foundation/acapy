import pytest
import time

from ..profile import IndySdkProfile
from ..wallet_setup import IndyWalletConfig, IndyOpenWallet


@pytest.fixture()
async def profile():
    yield IndySdkProfile(
        IndyOpenWallet(
            config=IndyWalletConfig({"name": "test-profile"}),
            created=True,
            handle=1,
            name="test-profile",
            master_secret_id="master-secret",
        )
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

    # FIXME needs more coverage
