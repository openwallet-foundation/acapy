from unittest import IsolatedAsyncioTestCase
import pytest

from acapy_agent.resolver.did_resolver import DIDResolver
from ...resolver.tests.test_did_resolver import MockResolver

from ...did.did_key import DIDKey
from ...utils.testing import create_test_profile
from ...wallet.default_verification_key_strategy import (
    DefaultVerificationKeyStrategy,
)

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"

class TestDefaultVerificationKeyStrategy(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        resolver = DIDResolver()
        resolver.register_resolver(
            MockResolver(
                ["example"],
                resolved= {
                    "@context": [
                        "https://www.w3.org/ns/did/v1",
                        "https://w3id.org/security/multikey/v1",
                    ],
                    "id": "did:example:123",
                    "verificationMethod": [
                        {
                            "id": "did:example:123#key-1",
                            "type": "Multikey",
                            "controller": "did:example:123",
                            "publicKeyMultibase": "z6MkjYXizfaAXTriV3h2Vc9uxJ9AMQpfG7mE1WKMnn1KJvFE",
                        },
                        {
                            "id": "did:example:123#key-2",
                            "type": "Multikey",
                            "controller": "did:example:123",
                            "publicKeyMultibase": "z6MkjYXizfaAXTriV3h2Vc9uxJ9AMQpfG7mE1WKMnn1KJvFE",
                        },
                        {
                            "id": "did:example:123#key-3",
                            "type": "Ed25519VerificationKey2018",
                            "controller": "did:example:123",
                            "publicKeyBase58": "66GgQRKjBvNFNYrKp3C57CbAXqYorEWsKVQRxW3JPhTr",
                        },
                    ],
                    "authentication": ["did:example:123#key-1"],
                    "assertionMethod": ["did:example:123#key-2", "did:example:123#key-3"],
                }
            )
        )
        self.profile.context.injector.bind_instance(DIDResolver, resolver)

    async def test_with_did_sov(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_SOV, self.profile)
            == TEST_DID_SOV + "#key-1"
        )

    async def test_with_did_key(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(TEST_DID_KEY, self.profile)
            == DIDKey.from_did(TEST_DID_KEY).key_id
        )
    
    async def test_with_did_for_assertion(self):
        strategy = DefaultVerificationKeyStrategy()
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2020",
                proof_purpose="assertionMethod"
            )
            == "did:example:123#key-2"
        )
        assert (
            await strategy.get_verification_method_id_for_did(
                "did:example:123",
                self.profile,
                proof_type="Ed25519Signature2018",
                proof_purpose="assertionMethod"
            )
            == "did:example:123#key-3"
        )

    async def test_unsupported_did_method(self):
        strategy = DefaultVerificationKeyStrategy()
        with pytest.raises(Exception):
            await strategy.get_verification_method_id_for_did(
                "did:test:test", self.profile
            )
