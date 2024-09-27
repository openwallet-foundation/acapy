"""Test Data Integrity Cryptosuites."""

from unittest import IsolatedAsyncioTestCase
from aries_cloudagent.wallet.keys.manager import MultikeyManager
from aries_cloudagent.vc.data_integrity.cryptosuites import EddsaJcs2022
from aries_cloudagent.wallet.in_memory import InMemoryWallet
from aries_cloudagent.core.in_memory import InMemoryProfile
from aries_cloudagent.vc.data_integrity.models.options import DataIntegrityProofOptions


class TestEddsaJcs2022(IsolatedAsyncioTestCase):
    """Tests for DI sign and verify."""

    profile = InMemoryProfile.test_profile()
    wallet = InMemoryWallet(profile)
    cryptosuite = "eddsa-jcs-2022"
    seed = "00000000000000000000000000000000"
    multikey = "z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i"

    unsecured_document = {"hello": "world"}
    options = DataIntegrityProofOptions.deserialize(
        {
            "type": "DataIntegrityProof",
            "cryptosuite": cryptosuite,
            "proofPurpose": "assertionMethod",
            "verificationMethod": f"did:key:{multikey}#{multikey}",
        }
    )

    async def asyncSetUp(self):
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
            assert verification["verified"]
