from unittest import TestCase as AsyncTestCase
import pytest
from aries_cloudagent.resolver.did_resolver import DIDResolver
from aries_cloudagent.resolver.tests.test_did_resolver import MockResolver
from aries_cloudagent.wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)

from aries_cloudagent.wallet.key_type import ED25519

from ...core.in_memory.profile import InMemoryProfile
from ...wallet.did_method import KEY, DIDMethods
from ...wallet.in_memory import InMemoryWallet

from ..jwt import jwt_sign, jwt_verify  # , resolve_public_key_by_kid_for_verify


@pytest.fixture()
async def profile():
    """In memory profile with injected dependencies."""

    mock_sov = MockResolver(
        ["key"],
        resolved={
            "@context": "https://www.w3.org/ns/did/v1",
            "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
            "verificationMethod": [
                {
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "type": "Ed25519VerificationKey2018",
                    "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "publicKeyBase58": "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx",
                }
            ],
            "authentication": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "assertionMethod": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "capabilityDelegation": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "capabilityInvocation": [
                "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
            ],
            "keyAgreement": [
                {
                    "id": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6LSbkodSr6SU2trs8VUgnrnWtSm7BAPG245ggrBmSrxbv1R",
                    "type": "X25519KeyAgreementKey2019",
                    "controller": "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL",
                    "publicKeyBase58": "5dTvYHaNaB7mk7iA9LqCJEHG2dGZQsvoi8WGzDRtYEf",
                }
            ],
        },
        native=True,
    )
    yield InMemoryProfile.test_profile(
        bind={
            DIDMethods: DIDMethods(),
            BaseVerificationKeyStrategy: DefaultVerificationKeyStrategy(),
            DIDResolver: DIDResolver([mock_sov]),
        }
    )


@pytest.fixture()
async def in_memory_wallet(profile):
    """In memory wallet for testing."""
    yield InMemoryWallet(profile)


@pytest.mark.ursa_jwt_signatures
class TestJWT:
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"
    did = "55GkHamhTU1ZbTbV2ab9DE"
    verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"

    @pytest.mark.asyncio
    async def test_sign_with_did_key(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        self.did = did_info.did
        verification_method = None

        headers = {}
        payload = {}
        signed = await jwt_sign(
            profile, headers, payload, self.did, verification_method
        )

        assert signed

        assert await jwt_verify(profile, signed)


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
