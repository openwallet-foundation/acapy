"""Test Data Integrity Cryptosuites."""

import pytest
from ..cryptosuites import CRYPTOSUITES
from ....wallet.key_type import ED25519
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile
from ....did.did_key import DIDKey


class TestEddsaJcs2022:
    """Tests for DI sign and verify."""

    test_seed = "00000000000000000000000000000000"
    unsecured_document = {"hello": "world"}
    options = {
        "type": "DataIntegrityProof",
        "cryptosuite": "eddsa-jcs-2022",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "did:key:z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i#z6MkgKA7yrw5kYSiDuQFcye4bMaJpcfHFry3Bx45pdWh3s8i",
    }

    async def asyncSetUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.cryptosuite = CRYPTOSUITES[self.options["cryptosuite"]](profile=self.profile)
        await InMemoryWallet(self.profile).create_signing_key(
            key_type=ED25519, seed=self.test_seed
        )

    async def test_add_proof(self):
        secured_document = self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        proof = secured_document.pop("proof", None)
        assert isinstance(proof, list)
        assert len(proof) == 1
        assert proof["type"] == self.options["type"]
        assert proof["cryptosuite"] == self.options["cryptosuite"]
        assert proof["proofPurpose"] == self.options["proofPurpose"]
        assert proof["verificationMethod"] == self.options["verificationMethod"]
        assert proof["proofValue"]

    async def test_proof_set(self):
        secured_document = self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        secured_document = self.cryptosuite.add_proof(secured_document, self.options)
        proof_set = proof_set.pop("proof", None)
        assert isinstance(proof_set, list)
        assert len(proof_set) == 2
        for proof in proof_set:
            assert proof["type"] == self.options["type"]
            assert proof["cryptosuite"] == self.options["cryptosuite"]
            assert proof["proofPurpose"] == self.options["proofPurpose"]
            assert proof["verificationMethod"] == self.options["verificationMethod"]
            assert proof["proofValue"]

    async def test_eddsa_jcs_2022_verify_proof(self):
        secured_document = self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        proof = secured_document.pop("proof", None)
        assert await self.cryptosuite.verify_proof(secured_document, proof)
        bad_proof = proof.copy()
        bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
        assert not await self.cryptosuite.verify_proof(secured_document, proof)

    async def test_eddsa_jcs_2022_verify_proof_set(self):
        secured_document = self.cryptosuite.add_proof(
            self.unsecured_document, self.options
        )
        secured_document = self.cryptosuite.add_proof(secured_document, self.options)
        proof_set = secured_document.pop("proof", None)
        for proof in proof_set:
            assert await self.cryptosuite.verify_proof(secured_document, proof)
            bad_proof = proof.copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            assert not await self.cryptosuite.verify_proof(secured_document, proof)
