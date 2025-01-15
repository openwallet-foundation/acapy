"""Test DataIntegrityManager."""

from unittest import IsolatedAsyncioTestCase

from acapy_agent.resolver.default.key import KeyDIDResolver
from acapy_agent.resolver.default.web import WebDIDResolver
from acapy_agent.resolver.did_resolver import DIDResolver
from acapy_agent.utils.testing import create_test_profile
from acapy_agent.vc.data_integrity.manager import DataIntegrityManager
from acapy_agent.vc.data_integrity.models.options import DataIntegrityProofOptions
from acapy_agent.wallet.key_type import KeyTypes
from acapy_agent.wallet.keys.manager import MultikeyManager


class TestDiManager(IsolatedAsyncioTestCase):
    """Tests for DI manager."""

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

    async def test_add_proof(self):
        async with self.profile.session() as session:
            secured_document = await DataIntegrityManager(session=session).add_proof(
                self.unsecured_document, self.options
            )
        proof = secured_document.pop("proof", None)
        assert isinstance(proof, list)
        assert len(proof) == 1
        assert proof[0]["type"] == self.options.type
        assert proof[0]["cryptosuite"] == self.options.cryptosuite
        assert proof[0]["proofPurpose"] == self.options.proof_purpose
        assert proof[0]["verificationMethod"] == self.options.verification_method
        assert proof[0]["proofValue"]

    async def test_add_proof_set(self):
        async with self.profile.session() as session:
            secured_document = await DataIntegrityManager(session=session).add_proof(
                self.unsecured_document, self.options
            )
            secured_document_with_proof_set = await DataIntegrityManager(
                session=session
            ).add_proof(secured_document, self.options)
        proof_set = secured_document_with_proof_set.pop("proof", None)
        assert isinstance(proof_set, list)
        assert len(proof_set) == 2
        for proof in proof_set:
            assert proof["type"] == self.options.type
            assert proof["cryptosuite"] == self.options.cryptosuite
            assert proof["proofPurpose"] == self.options.proof_purpose
            assert proof["verificationMethod"] == self.options.verification_method
            assert proof["proofValue"]

    async def test_add_proof_chain(self):
        pass

    async def test_verify_proof(self):
        async with self.profile.session() as session:
            di_manager = DataIntegrityManager(session=session)
            secured_document = await di_manager.add_proof(
                self.unsecured_document, self.options
            )
            verification = await di_manager.verify_proof(secured_document)
            assert verification.verified
            bad_proof = secured_document["proof"][0].copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            secured_document["proof"][0] = bad_proof
            verification = await di_manager.verify_proof(secured_document)
            assert not verification.verified

    async def test_verify_proof_set(self):
        async with self.profile.session() as session:
            di_manager = DataIntegrityManager(session=session)
            secured_document = await di_manager.add_proof(
                self.unsecured_document, self.options
            )
            secured_document_with_proof_set = await di_manager.add_proof(
                secured_document, self.options
            )
            verification = await di_manager.verify_proof(secured_document_with_proof_set)
            assert verification.verified
            bad_proof = secured_document_with_proof_set["proof"][0].copy()
            bad_proof["proofValue"] = bad_proof["proofValue"][:-1]
            secured_document_with_proof_set["proof"][0] = bad_proof
            verification = await di_manager.verify_proof(secured_document_with_proof_set)
            assert not verification.verified

    async def test_verify_proof_chain(self):
        # TODO, add tests once proof chain support is added
        pass
