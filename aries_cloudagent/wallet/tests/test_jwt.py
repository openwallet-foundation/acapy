from unittest import TestCase as AsyncTestCase
import pytest

from aries_cloudagent.core.in_memory.profile import InMemoryProfile

from ..jwt import jwt_sign, jwt_verify, resolve_public_key_by_kid_for_verify


@pytest.mark.ursa_jwt_signatures
class TestJWT(AsyncTestCase):
    async def test_sign(self):
        mock_profile = InMemoryProfile.test_profile()
        # did =
        # verification_method =
        # headers =
        # payload =
        signed = await jwt_sign(
            mock_profile, headers, payload, did, verification_method
        )

        assert signed

        assert await jwt_verify(mock_profile, signed)


"""
    async def test_sign_x_invalid_secret_key_bytes(self):
        mock_profile = InMemoryProfile.test_profile()
        with self.assertRaises(Exception) as context:
            jwt_sign(SIGN_MESSAGES, "hello")
        assert "Unable to sign messages" in str(context.exception)

    async def test_verify(self):
        mock_profile = InMemoryProfile.test_profile()
        assert jwt_verify(
            SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES
        )

    async def test_verify_x_invalid_pk(self):
        mock_profile = InMemoryProfile.test_profile()
        with self.assertRaises(Exception):
            jwt_verify(
                SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES + b"10"
            )

    async def test_verify_x_invalid_messages(self):
        mock_profile = InMemoryProfile.test_profile()
        with self.assertRaises(Exception):
            jwt_verify(
                SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES + b"10"
            )
        assert not jwt_verify(
            [SIGN_MESSAGES[0]], SIGNED_BYTES, PUBLIC_KEY_BYTES
        )

    async def test_verify_x_invalid_signed_bytes(self):
        mock_profile = InMemoryProfile.test_profile()
        with self.assertRaises(Exception):
            assert not jwt_verify(
                SIGN_MESSAGES, SIGNED_BYTES + b"10", PUBLIC_KEY_BYTES
            )

    async def test_resolve_public_key_by_kid_for_verify(self):
        mock_profile = InMemoryProfile.test_profile()
"""
