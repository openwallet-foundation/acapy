"""Test Data Integrity Cryptosuites."""

from unittest import IsolatedAsyncioTestCase

from acapy_agent.resolver.default.key import KeyDIDResolver
from acapy_agent.resolver.default.web import WebDIDResolver
from acapy_agent.resolver.did_resolver import DIDResolver
from acapy_agent.utils.testing import create_test_profile
from acapy_agent.vc.data_integrity.cryptosuites import EddsaJcs2022
from acapy_agent.vc.data_integrity.models.options import DataIntegrityProofOptions
from acapy_agent.wallet.key_type import KeyTypes
from acapy_agent.wallet.keys.manager import MultikeyManager


class TestEddsaJcs2022(IsolatedAsyncioTestCase):
    """Tests for DI sign and verify."""

    async def asyncSetUp(self):
        self.seed = "00000000000000000000000000000000"
        self.multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"
        self.verification_method = f"did:key:{self.multikey}#{self.multikey}"
        self.cryptosuite = "eddsa-jcs-2022"
        self.unsecured_document = {"hello": "world"}
        self.options = DataIntegrityProofOptions.deserialize(
            {
                "type": "DataIntegrityProof",
                "cryptosuite": self.cryptosuite,
                "proofPurpose": "assertionMethod",
                "verificationMethod": self.verification_method,
            }
        )

        self.resolver = DIDResolver()
        self.resolver.register_resolver(KeyDIDResolver())
        self.resolver.register_resolver(WebDIDResolver())
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(DIDResolver, self.resolver)
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())
        try:
            async with self.profile.session() as session:
                await MultikeyManager(session=session).create(seed=self.seed)
        except Exception:
            pass

    async def test_create_proof(self):
        async with self.profile.session() as session:
            proof = await EddsaJcs2022(session=session).create_proof(
                self.unsecured_document, self.options
            )
            proof = proof.serialize()
            assert isinstance(proof, dict)
            assert proof["type"] == self.options.type
            assert proof["cryptosuite"] == self.options.cryptosuite
            assert proof["proofPurpose"] == self.options.proof_purpose
            assert proof["verificationMethod"] == self.options.verification_method
            assert proof["proofValue"]

    async def test_verify_proof(self):
        async with self.profile.session() as session:
            cryptosuite_instance = EddsaJcs2022(session=session)
            proof = await cryptosuite_instance.create_proof(
                self.unsecured_document, self.options
            )
            secured_document = self.unsecured_document | {"proof": proof.serialize()}
            verification = await cryptosuite_instance.verify_proof(secured_document)
            assert verification.verified
