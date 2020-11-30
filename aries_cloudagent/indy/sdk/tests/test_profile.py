import pytest
import time

from ..profile import IndySdkProfile


@pytest.fixture()
async def profile():
    yield IndySdkProfile("test-profile")


class TestIndySdkProfile:
    @pytest.mark.asyncio
    async def test_properties(self, profile):
        assert profile.name
        assert profile.backend == "indy"
        assert profile.wallet and profile.wallet.handle

        assert "IndySdkProfile" in str(profile)
        assert profile.wallet.created
        assert profile.wallet.master_secret_id == profile.wallet.name
        assert profile.wallet._wallet_config

    # FIXME needs more coverage
