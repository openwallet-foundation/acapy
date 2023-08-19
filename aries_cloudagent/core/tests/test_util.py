from unittest import IsolatedAsyncioTestCase

from ...cache.base import BaseCache
from ...cache.in_memory import InMemoryCache
from ...core.in_memory import InMemoryProfile
from ...core.profile import Profile
from ...protocols.didcomm_prefix import DIDCommPrefix
from ...protocols.introduction.v0_1.messages.invitation import Invitation
from ...protocols.out_of_band.v1_0.messages.reuse import HandshakeReuse

from .. import util as test_module


def make_profile() -> Profile:
    profile = InMemoryProfile.test_profile()
    profile.context.injector.bind_instance(BaseCache, InMemoryCache())
    return profile


class TestUtils(IsolatedAsyncioTestCase):
    async def test_validate_get_response_version(self):
        profile = make_profile()
        (resp_version, warning) = await test_module.validate_get_response_version(
            profile, "1.1", HandshakeReuse
        )
        assert resp_version == "1.1"
        assert not warning

        # cached
        (resp_version, warning) = await test_module.validate_get_response_version(
            profile, "1.1", HandshakeReuse
        )
        assert resp_version == "1.1"
        assert not warning

        (resp_version, warning) = await test_module.validate_get_response_version(
            profile, "1.0", HandshakeReuse
        )
        assert resp_version == "1.0"
        assert warning == test_module.WARNING_DEGRADED_FEATURES

        (resp_version, warning) = await test_module.validate_get_response_version(
            profile, "1.2", HandshakeReuse
        )
        assert resp_version == "1.1"
        assert warning == test_module.WARNING_VERSION_MISMATCH

        with self.assertRaises(test_module.ProtocolMinorVersionNotSupported):
            (resp_version, warning) = await test_module.validate_get_response_version(
                profile, "0.0", Invitation
            )

        with self.assertRaises(Exception):
            (resp_version, warning) = await test_module.validate_get_response_version(
                profile, "1.0", Invitation
            )

    def test_get_version_from_message_type(self):
        assert (
            test_module.get_version_from_message_type(
                DIDCommPrefix.qualify_current("out-of-band/1.1/handshake-reuse")
            )
            == "1.1"
        )

    def test_get_version_from_message(self):
        assert test_module.get_version_from_message(HandshakeReuse()) == "1.1"

    async def test_get_proto_default_version_from_msg_class(self):
        profile = make_profile()
        assert (
            await test_module.get_proto_default_version_from_msg_class(
                profile, HandshakeReuse
            )
        ) == "1.1"

    def test_get_proto_default_version(self):
        assert (
            test_module.get_proto_default_version(
                "aries_cloudagent.protocols.out_of_band.definition"
            )
        ) == "1.1"
