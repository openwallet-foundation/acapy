from unittest import IsolatedAsyncioTestCase

import pytest

from acapy_agent.resolver.did_resolver import DIDResolver
from acapy_agent.wallet.key_type import KeyTypes
from acapy_agent.wallet.keys.manager import MultikeyManager

from ...did.did_key import DIDKey
from ...resolver.tests.test_did_resolver import MockResolver
from ...utils.testing import create_test_profile
from ...wallet.default_verification_key_strategy import DefaultVerificationKeyStrategy

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_SEED = "testseed000000000000000000000001"
TEST_ED25519_MULTIKEY = "z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_ED25519_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_BLS_G2_MULTIKEY = "zUC74E9UD2W6Q1MgPexCEdpstiCsY1Vbnyqepygk7McZVce38L1tGX7qZ2SgY4Zz2m9FUB4Xb5cEHSujks9XeKDzqe4QzW3CyyJ1cv8iBLNqU61EfkBoW2yEkg6VgqHTDtANYRS"
TEST_BLS_G2_VERKEY = "pPbb9Lqs3PVTyiHM4h8fbQqxHjBPm1Hixb6vdW9kkjHEij4FZrigkaV1P5DjWTbcKxeeYfkQuZMmozRQV3tH1gXhCA972LAXMGSKH7jxz8sNJqrCR6o8asgXDeYZeL1W3p8"
TEST_DID_KEY = f"did:key:{TEST_ED25519_MULTIKEY}"


class TestDefaultVerificationKeyStrategy(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        resolver = DIDResolver()
        resolver.register_resolver(
            MockResolver(
                ["example"],
                resolved={
                    "@context": [
                        "https://www.w3.org/ns/did/v1",
                        "https://w3id.org/security/multikey/v1",
                    ],
                    "id": "did:example:123",
                    "verificationMethod": [
                        # VM has a key not owned by this acapy agent
                        {
                            "id": "did:example:123#not-owned",
                            "type": "Multikey",
                            "controller": "did:example:123",
                            "publicKeyMultibase": "z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDHHyGo38EefXmgDL",
                        },
                        {
                            "id": "did:example:123#key-1",
                            "type": "Multikey",
                            "controller": "did:example:123",
                            "publicKeyMultibase": TEST_ED25519_MULTIKEY,
                        },
                        {
                            "id": "did:example:123#key-2",
                            "type": "Multikey",
                            "controller": "did:example:123",
                            "publicKeyMultibase": TEST_ED25519_MULTIKEY,
                        },
                        {
                            "id": "did:example:123#key-3",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:example:123",
                            "publicKeyBase58": TEST_ED25519_VERKEY,
                        },
                    ],
                    "authentication": ["did:example:123#key-1"],
                    "assertionMethod": [
                        "did:example:123#not-owned",
                        "did:example:123#key-2",
                        "did:example:123#key-3",
                        {
                            "id": "did:example:123#key-4",
                            "type": "Bls12381G2Key2020",
                            "controller": "did:example:123",
                            "publicKeyBase58": TEST_BLS_G2_VERKEY,
                        },
                    ],
                },
            )
        )
        self.profile.context.injector.bind_instance(DIDResolver, resolver)
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())
        async with self.profile.session() as session:
            await MultikeyManager(session=session).create(seed=TEST_SEED, alg="ed25519")
            await MultikeyManager(session=session).create(
                seed=TEST_SEED, alg="bls12381g2"
            )

    async def test_with_did_sov(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_SOV, self.profile)
            == TEST_DID_SOV + "#key-1"
        )
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                did=TEST_DID_SOV,
                profile=self.profile,
                proof_type="BbsBlsSignature2020",
            )
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                did=TEST_DID_SOV,
                profile=self.profile,
                verification_method_id=f"{TEST_DID_KEY}#key-2",
            )

    async def test_with_did_key(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_KEY, self.profile)
            == DIDKey.from_did(TEST_DID_KEY).key_id
        )
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                did=TEST_DID_KEY,
                profile=self.profile,
                proof_type="BbsBlsSignature2020",
            )
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                did=TEST_DID_KEY,
                profile=self.profile,
                verification_method_id=f"{TEST_DID_KEY}#abc",
            )

    async def test_with_did_for_assertion(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2020",
                proof_purpose="assertionMethod",
            )
            == "did:example:123#key-2"
        )
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2018",
                proof_purpose="assertionMethod",
            )
            == "did:example:123#key-2"
        )
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2018",
                proof_purpose="assertionMethod",
                verification_method_id="did:example:123#key-3",
            )
            == "did:example:123#key-3"
        )
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="BbsBlsSignature2020",
                proof_purpose="assertionMethod",
            )
            == "did:example:123#key-4"
        )

    async def test_fail_cases(self):
        strategy = DefaultVerificationKeyStrategy()
        # base case
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2020",
                proof_purpose="assertionMethod",
                verification_method_id="did:example:123#key-2",
            )
            == "did:example:123#key-2"
        )
        with pytest.raises(Exception):
            # nothing suitable for purpose
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2020",
                proof_purpose="capabilityInvocation",
            )
        with pytest.raises(Exception):
            # nothing suitable for proof type
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="EcdsaSecp256r1Signature2019",
                proof_purpose="assertionMethod",
            )
        with pytest.raises(Exception):
            # suitable, but key not owned by acapy
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2020",
                proof_purpose="assertionMethod",
                verification_method_id="did:example:123#not-owned",
            )

    async def test_unsupported_did_method(self):
        strategy = DefaultVerificationKeyStrategy()
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                "did:test:test", self.profile
            )
