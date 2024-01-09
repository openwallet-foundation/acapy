"""Test PeerDIDResolver."""

import pytest

from aries_cloudagent.core.event_bus import EventBus

from ....core.in_memory import InMemoryProfile
from ....core.profile import Profile
from .. import peer4 as test_module
from ..peer4 import PeerDID4Resolver

# https://identity.foundation/peer-did-method-spec/#method-4-short-form-and-long-form
TEST_LONG_DP4 = "did:peer:4zQmd8CpeFPci817KDsbSAKWcXAE2mjvCQSasRewvbSF54Bd:z2M1k7h4psgp4CmJcnQn2Ljp7Pz7ktsd7oBhMU3dWY5s4fhFNj17qcRTQ427C7QHNT6cQ7T3XfRh35Q2GhaNFZmWHVFq4vL7F8nm36PA9Y96DvdrUiRUaiCuXnBFrn1o7mxFZAx14JL4t8vUWpuDPwQuddVo1T8myRiVH7wdxuoYbsva5x6idEpCQydJdFjiHGCpNc2UtjzPQ8awSXkctGCnBmgkhrj5gto3D4i3EREXYq4Z8r2cWGBr2UzbSmnxW2BuYddFo9Yfm6mKjtJyLpF74ytqrF5xtf84MnGFg1hMBmh1xVx1JwjZ2BeMJs7mNS8DTZhKC7KH38EgqDtUZzfjhpjmmUfkXg2KFEA3EGbbVm1DPqQXayPYKAsYPS9AyKkcQ3fzWafLPP93UfNhtUPL8JW5pMcSV3P8v6j3vPXqnnGknNyBprD6YGUVtgLiAqDBDUF3LSxFQJCVYYtghMTv8WuSw9h1a1SRFrDQLGHE4UrkgoRvwaGWr64aM87T1eVGkP5Dt4L1AbboeK2ceLArPScrdYGTpi3BpTkLwZCdjdiFSfTy9okL1YNRARqUf2wm8DvkVGUU7u5nQA3ZMaXWJAewk6k1YUxKd7LvofGUK4YEDtoxN5vb6r1Q2godrGqaPkjfL3RoYPpDYymf9XhcgG8Kx3DZaA6cyTs24t45KxYAfeCw4wqUpCH9HbpD78TbEUr9PPAsJgXBvBj2VVsxnr7FKbK4KykGcg1W8M1JPz21Z4Y72LWgGQCmixovrkHktcTX1uNHjAvKBqVD5C7XmVfHgXCHj7djCh3vzLNuVLtEED8J1hhqsB1oCBGiuh3xXr7fZ9wUjJCQ1HYHqxLJKdYKtoCiPmgKM7etVftXkmTFETZmpM19aRyih3bao76LdpQtbw636r7a3qt8v4WfxsXJetSL8c7t24SqQBcAY89FBsbEnFNrQCMK3JEseKHVaU388ctvRD45uQfe5GndFxthj4iSDomk4uRFd1uRbywoP1tRuabHTDX42UxPjz"
TEST_SHORT_DP4 = "did:peer:4zQmd8CpeFPci817KDsbSAKWcXAE2mjvCQSasRewvbSF54Bd"


@pytest.fixture
def event_bus():
    yield EventBus()


@pytest.fixture
def profile(event_bus: EventBus):
    """Profile fixture."""
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(EventBus, event_bus)
    yield profile


@pytest.fixture
async def resolver(profile):
    """Resolver fixture."""
    instance = PeerDID4Resolver()
    await instance.setup(profile.context)
    yield instance


@pytest.mark.asyncio
async def test_resolve_4(profile: Profile, resolver: PeerDID4Resolver):
    """Test resolver setup."""
    assert resolver.supported_did_regex
    assert await resolver.supports(profile, TEST_LONG_DP4)
    assert await resolver.supports(profile, TEST_SHORT_DP4)

    long_doc = await resolver.resolve(profile, TEST_LONG_DP4)
    short_doc = await resolver.resolve(profile, TEST_SHORT_DP4)

    assert long_doc["id"] == TEST_LONG_DP4
    assert TEST_SHORT_DP4 in long_doc["alsoKnownAs"]
    assert short_doc["id"] == TEST_SHORT_DP4


@pytest.mark.asyncio
async def test_resolve_x_no_long(profile: Profile, resolver: PeerDID4Resolver):
    """Test resolver setup."""
    with pytest.raises(test_module.DIDNotFound):
        await resolver.resolve(profile, TEST_SHORT_DP4)
