from unittest import TestCase
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

from ..jwt import jwt_sign, jwt_verify, resolve_public_key_by_kid_for_verify


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


class TestJWT:
    """Tests for JWT sign and verify using dids."""

    seed = "testseed000000000000000000000001"

    @pytest.mark.asyncio
    async def test_sign_with_did_key_and_verify(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = did_info.did
        verification_method = None

        headers = {}
        payload = {}
        signed = await jwt_sign(profile, headers, payload, did, verification_method)

        assert signed

        assert await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_sign_with_verification_method_and_verify(
        self, profile, in_memory_wallet
    ):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = None
        verification_method = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        headers = {}
        payload = {}
        signed: str = await jwt_sign(
            profile, headers, payload, did, verification_method
        )

        assert signed

        assert await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_sign_x_invalid_did(self, profile):
        did = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        headers = {}
        payload = {}
        verification_method = None
        with pytest.raises(Exception) as e_info:
            await jwt_sign(profile, headers, payload, did, verification_method)
        assert "No key type for prefixed public key" in str(e_info)

    @pytest.mark.asyncio
    async def test_sign_x_invalid_verification_method(self, profile):
        did = None
        headers = {}
        payload = {}
        verification_method = "did:key:zzzzgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        with pytest.raises(Exception) as e_info:
            await jwt_sign(profile, headers, payload, did, verification_method)
        assert "DID not found:" in str(e_info)

    @pytest.mark.asyncio
    async def test_verify_x_invalid_signed(self, profile, in_memory_wallet):
        did_info = await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        did = did_info.did
        verification_method = None

        headers = {}
        payload = {}
        signed = await jwt_sign(profile, headers, payload, did, verification_method)

        assert signed
        signed = f"{signed[:-2]}2"

        with pytest.raises(Exception) as e_info:
            await jwt_verify(profile, signed)

    @pytest.mark.asyncio
    async def test_resolve_public_key_by_kid_for_verify(
        self, profile, in_memory_wallet
    ):
        await in_memory_wallet.create_local_did(KEY, ED25519, self.seed)
        kid = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
        key_material = await resolve_public_key_by_kid_for_verify(profile, kid)

        assert key_material == "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
