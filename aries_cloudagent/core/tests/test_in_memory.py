import pytest
import time

from ..in_memory import InMemoryProfile


@pytest.fixture()
async def profile():
    yield InMemoryProfile.test_profile()


class TestInMemoryWallet:
    @pytest.mark.asyncio
    async def test_properties(self, profile):
        assert profile.name == "test-profile"
        assert profile.backend == "in_memory"

        assert "InMemoryProfile" in str(profile)
        # assert profile.created
