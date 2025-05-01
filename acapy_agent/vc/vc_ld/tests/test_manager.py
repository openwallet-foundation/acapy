"""Test VcLdpManager."""

from unittest import IsolatedAsyncioTestCase

import pytest

from acapy_agent.tests import mock
from acapy_agent.wallet.keys.manager import MultikeyManager

from ....did.did_key import DIDKey
from ....resolver.default.key import KeyDIDResolver
from ....resolver.did_resolver import DIDResolver
from ....storage.vc_holder.base import VCHolder
from ....utils.testing import create_test_profile
from ....wallet.base import BaseWallet
from ....wallet.default_verification_key_strategy import (
    BaseVerificationKeyStrategy,
    DefaultVerificationKeyStrategy,
)
from ....wallet.did_method import KEY, SOV, DIDMethod, DIDMethods
from ....wallet.key_type import BLS12381G2, ED25519, KeyTypes
from ...ld_proofs.constants import (
    SECURITY_CONTEXT_BBS_URL,
    SECURITY_CONTEXT_ED25519_2020_URL,
)
from ...ld_proofs.crypto.wallet_key_pair import WalletKeyPair
from ...ld_proofs.document_loader import DocumentLoader
from ...ld_proofs.purposes.authentication_proof_purpose import AuthenticationProofPurpose
from ...ld_proofs.purposes.credential_issuance_purpose import CredentialIssuancePurpose
from ...ld_proofs.suites.bbs_bls_signature_2020 import BbsBlsSignature2020
from ...ld_proofs.suites.bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020
from ...ld_proofs.suites.ecdsa_secp256r1_signature_2019 import EcdsaSecp256r1Signature2019
from ...ld_proofs.suites.ed25519_signature_2018 import Ed25519Signature2018
from ...ld_proofs.suites.ed25519_signature_2020 import Ed25519Signature2020
from ..manager import VcLdpManager, VcLdpManagerError
from ..models.credential import VerifiableCredential
from ..models.options import LDProofVCOptions

TEST_DID_SOV = "did:sov:LjgpST2rjsoxYegQDRm7EL"
TEST_DID_KEY = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_DID_KEY_SEED = "testseed000000000000000000000001"
TEST_DID_KEY_VM = "did:key:z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL#z6Mkgg342Ycpuk263R9d8Aq6MUaxPn1DDeHyGo38EefXmgDL"
TEST_DID_KEY_VERKEY = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
TEST_UUID = "urn:uuid:dc86e95c-dc85-4f91-b563-82657d095c44"
VC = {
    "credential": {
        "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://www.w3.org/2018/credentials/examples/v1",
            {
                "ex": "https://example.org/test#",
                "test": "ex:test",
            },
        ],
        "type": ["VerifiableCredential", "UniversityDegreeCredential"],
        "credentialSubject": {"test": "key"},
        "issuanceDate": "2021-04-12",
        "issuer": TEST_DID_KEY,
    },
    "options": {
        "proofType": "Ed25519Signature2018",
        "created": "2019-12-11T03:50:55",
    },
}


class TestVcLdManager(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.profile = await create_test_profile()
        self.profile.context.injector.bind_instance(KeyTypes, KeyTypes())
        self.profile.context.injector.bind_instance(
            DIDResolver, DIDResolver([KeyDIDResolver()])
        )
        self.profile.context.injector.bind_instance(
            DefaultVerificationKeyStrategy, DefaultVerificationKeyStrategy()
        )
        self.profile.context.injector.bind_instance(
            BaseVerificationKeyStrategy,
            DefaultVerificationKeyStrategy(),
        )
        self.profile.context.injector.bind_instance(DIDMethods, DIDMethods())

        self.profile.context.injector.bind_instance(
            DocumentLoader, DocumentLoader(self.profile)
        )
        self.manager = VcLdpManager(self.profile)
        self.vc = VerifiableCredential.deserialize(VC["credential"])
        self.options = LDProofVCOptions.deserialize(VC["options"])

        async with self.profile.session() as session:
            await MultikeyManager(session=session).create(
                seed=TEST_DID_KEY_SEED, alg="ed25519"
            )

    methods: list[DIDMethod] = [SOV, KEY]

    async def test_get_did_info_for_did_sov(self):
        for method in self.methods:
            async with self.profile.session() as session:
                wallet = session.inject(BaseWallet)
                did = await wallet.create_local_did(
                    method=method,
                    key_type=ED25519,
                )
            did_info = await self.manager._did_info_for_did(did.did)
            assert did_info == did

    async def test_get_suite_for_document(self):
        with (
            mock.patch.object(
                self.manager,
                "_did_info_for_did",
                mock.CoroutineMock(),
            ) as mock_did_info,
        ):
            suite = await self.manager._get_suite_for_document(self.vc, self.options)

            assert suite.signature_type == self.options.proof_type
            assert isinstance(suite, Ed25519Signature2018)
            assert suite.verification_method == DIDKey.from_did(TEST_DID_KEY).key_id
            assert suite.proof == {"created": VC["options"]["created"]}
            assert isinstance(suite.key_pair, WalletKeyPair)
            assert suite.key_pair.key_type == ED25519
            assert suite.key_pair.public_key_base58 == TEST_DID_KEY_VERKEY

            mock_did_info.assert_awaited_once_with(self.vc.issuer)

    async def test_get_suite(self):
        proof = mock.MagicMock()
        did_info = mock.MagicMock()

        suite = await self.manager._get_suite(
            proof_type=BbsBlsSignature2020.signature_type,
            verification_method=TEST_DID_KEY_VM,
            proof=proof,
            did_info=did_info,
        )

        assert isinstance(suite, BbsBlsSignature2020)
        assert suite.verification_method == TEST_DID_KEY_VM
        assert suite.proof == proof
        assert isinstance(suite.key_pair, WalletKeyPair)
        assert suite.key_pair.key_type == BLS12381G2
        assert suite.key_pair.public_key_base58 == TEST_DID_KEY_VERKEY

        suite = await self.manager._get_suite(
            proof_type=Ed25519Signature2018.signature_type,
            verification_method=TEST_DID_KEY_VM,
            proof=proof,
            did_info=did_info,
        )

        assert isinstance(suite, Ed25519Signature2018)
        assert suite.verification_method == TEST_DID_KEY_VM
        assert suite.proof == proof
        assert isinstance(suite.key_pair, WalletKeyPair)
        assert suite.key_pair.key_type == ED25519
        assert suite.key_pair.public_key_base58 == TEST_DID_KEY_VERKEY

        suite = await self.manager._get_suite(
            proof_type=Ed25519Signature2020.signature_type,
            verification_method=TEST_DID_KEY_VM,
            proof=proof,
            did_info=did_info,
        )

        assert isinstance(suite, Ed25519Signature2020)
        assert suite.verification_method == TEST_DID_KEY_VM
        assert suite.proof == proof
        assert isinstance(suite.key_pair, WalletKeyPair)
        assert suite.key_pair.key_type == ED25519
        assert suite.key_pair.public_key_base58 == TEST_DID_KEY_VERKEY

    async def test_get_proof_purpose(self):
        purpose = self.manager._get_proof_purpose()
        assert isinstance(purpose, CredentialIssuancePurpose)

        purpose = self.manager._get_proof_purpose(
            proof_purpose=AuthenticationProofPurpose.term,
            challenge="challenge",
            domain="domain",
        )
        assert isinstance(purpose, AuthenticationProofPurpose)
        assert purpose.domain == "domain"
        assert purpose.challenge == "challenge"

        with pytest.raises(VcLdpManagerError) as context:
            self.manager._get_proof_purpose(proof_purpose=AuthenticationProofPurpose.term)
        assert "Challenge is required for" in str(context.value)

        with pytest.raises(VcLdpManagerError) as context:
            self.manager._get_proof_purpose(proof_purpose="random")
        assert "Unsupported proof purpose: random" in str(context.value)

    async def test_prepare_detail(self):
        self.options.proof_type = BbsBlsSignature2020.signature_type

        assert SECURITY_CONTEXT_BBS_URL not in self.vc.context_urls

        await self.manager.prepare_credential(self.vc, self.options)

        assert SECURITY_CONTEXT_BBS_URL in self.vc.context_urls

    async def test_prepare_detail_ed25519_2020(self):
        self.options.proof_type = Ed25519Signature2020.signature_type

        assert SECURITY_CONTEXT_ED25519_2020_URL not in self.vc.context_urls

        await self.manager.prepare_credential(self.vc, self.options)

        assert SECURITY_CONTEXT_ED25519_2020_URL in self.vc.context_urls

    async def test_issue(self):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did = await wallet.create_local_did(
                method=KEY,
                key_type=ED25519,
            )
        self.vc.issuer = did.did
        self.options.proof_type = Ed25519Signature2018.signature_type
        cred = await self.manager.issue(self.vc, self.options)
        assert cred

    async def test_issue_ed25519_2020(self):
        """Ensure ed25519 2020 context added to issued cred."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did = await wallet.create_local_did(
                method=KEY,
                key_type=ED25519,
            )
        self.vc.issuer = did.did
        self.options.proof_type = Ed25519Signature2020.signature_type
        cred = await self.manager.issue(self.vc, self.options)
        assert cred

    @pytest.mark.ursa_bbs_signatures
    async def test_issue_bbs(self):
        """Ensure BBS context is added to issued cred."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did = await wallet.create_local_did(
                method=KEY,
                key_type=BLS12381G2,
            )
        self.vc.issuer = did.did
        self.options.proof_type = BbsBlsSignature2020.signature_type
        cred = await self.manager.issue(self.vc, self.options)
        assert cred

    async def test_get_all_suites(self):
        suites = await self.manager._get_all_proof_suites()
        assert len(suites) == 5
        types = (
            Ed25519Signature2018,
            Ed25519Signature2020,
            EcdsaSecp256r1Signature2019,
            BbsBlsSignature2020,
            BbsBlsSignatureProof2020,
        )
        for suite in suites:
            assert isinstance(suite, types)

    async def test_store(
        self,
    ):
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            did = await wallet.create_local_did(
                method=KEY,
                key_type=ED25519,
            )
        self.vc.issuer = did.did
        self.options.proof_type = Ed25519Signature2018.signature_type
        cred = await self.manager.issue(self.vc, self.options)
        await self.manager.store_credential(cred, TEST_UUID)
        async with self.profile.session() as session:
            holder = session.inject(VCHolder)
            record = await holder.retrieve_credential_by_id(record_id=TEST_UUID)
        assert record
