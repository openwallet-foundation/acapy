"""Test Data Integrity Cryptosuites."""

from unittest import IsolatedAsyncioTestCase
from ..cryptosuites import CRYPTOSUITES
from ....wallet.key_type import ED25519
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ....wallet.did_method import KEY, DIDMethods

TEST_SEED = "00000000000000000000000000000000"


class TestEddsaJcs2022(IsolatedAsyncioTestCase):
    """Tests for DI sign and verify."""

    unsecured_document = {"hello": "world"}
    options = {
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-jcs-2022",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i#z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i",
    }

    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile({}, {DIDMethods: DIDMethods()})
        self.wallet = InMemoryWallet(self.profile)
        await self.wallet.create_local_did(method=KEY, key_type=ED25519, seed=TEST_SEED)
        self.cryptosuite = CRYPTOSUITES[self.options["cryptosuite"]](profile=self.profile)

    async def test_add_proof(self):
        secured_document = await self.cryptosuite.add_proof(
            document=self.unsecured_document, proof_options=self.options
        )
        proof = secured_document.pop("proof", None)
        assert isinstance(proof, list)
        assert len(proof) == 1
        assert proof[0]["type"] == self.options["type"]
        assert proof[0]["cryptosuite"] == self.options["cryptosuite"]
        assert proof[0]["proofPurpose"] == self.options["proofPurpose"]
        assert proof[0]["verificationMethod"] == self.options["verificationMethod"]
        assert proof[0]["proofValue"]

    async def test_proof_set(self):
        secured_document = await self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        secured_document = await self.cryptosuite.add_proof(
            secured_document, self.options
        )
        proof_set = secured_document.pop("proof", None)
        assert isinstance(proof_set, list)
        assert len(proof_set) == 2
        for proof in proof_set:
            assert proof["type"] == self.options["type"]
            assert proof["cryptosuite"] == self.options["cryptosuite"]
            assert proof["proofPurpose"] == self.options["proofPurpose"]
            assert proof["verificationMethod"] == self.options["verificationMethod"]
            assert proof["proofValue"]

    async def test_eddsa_jcs_2022_verify_proof(self):
        secured_document = await self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        proof = secured_document.pop("proof", None)
        assert await self.cryptosuite.verify_proof(secured_document, proof[0])
        bad_proof = proof[0].copy()
        bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
        assert not await self.cryptosuite.verify_proof(secured_document, bad_proof)

    async def test_eddsa_jcs_2022_verify_proof_set(self):
        secured_document = await self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        secured_document = await self.cryptosuite.add_proof(
            secured_document, self.options
        )
        proof_set = secured_document.pop("proof", None)
        for proof in proof_set:
            assert await self.cryptosuite.verify_proof(secured_document, proof)
            bad_proof = proof.copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            assert not await self.cryptosuite.verify_proof(secured_document, bad_proof)
