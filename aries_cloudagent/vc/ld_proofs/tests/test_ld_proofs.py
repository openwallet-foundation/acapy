import pytest

from datetime import datetime, timezone

from asynctest import TestCase

from ....wallet.key_type import BLS12381G2, ED25519
from ....did.did_key import DIDKey
from ....wallet.in_memory import InMemoryWallet
from ....core.in_memory import InMemoryProfile

from ...ld_proofs import (
    sign,
    Ed25519Signature2018,
    Ed25519Signature2020,
    WalletKeyPair,
    AssertionProofPurpose,
    verify,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    derive,
)
from ...tests.document_loader import custom_document_loader

from .test_doc import (
    DOC_DERIVED_BBS,
    DOC_SIGNED_BBS,
    DOC_TEMPLATE,
    DOC_TEMPLATE_2020,
    DOC_SIGNED,
    DOC_SIGNED_2020,
    DOC_TEMPLATE_BBS,
    DOC_FRAME_BBS,
    DOC_VERIFIED,
    DOC_VERIFIED_2020,
)


class TestLDProofs(TestCase):
    test_seed = "testseed000000000000000000000001"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)

        self.ed25519_key_info = await self.wallet.create_signing_key(
            key_type=ED25519, seed=self.test_seed
        )
        self.ed25519_verification_method = DIDKey.from_public_key_b58(
            self.ed25519_key_info.verkey, ED25519
        ).key_id

        self.bls12381g2_key_info = await self.wallet.create_signing_key(
            key_type=BLS12381G2, seed=self.test_seed
        )

        self.bls12381g2_verification_method = DIDKey.from_public_key_b58(
            self.bls12381g2_key_info.verkey, BLS12381G2
        ).key_id

    async def test_sign_Ed25519Signature2018(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = Ed25519Signature2018(
            verification_method=self.ed25519_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=ED25519,
                public_key_base58=self.ed25519_key_info.verkey,
            ),
            date=datetime(2019, 12, 11, 3, 50, 55, 0, timezone.utc),
        )
        signed = await sign(
            document=DOC_TEMPLATE,
            suite=suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert signed == DOC_SIGNED

    async def test_sign_Ed25519Signature2020(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = Ed25519Signature2020(
            verification_method=self.ed25519_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=ED25519,
                public_key_base58=self.ed25519_key_info.verkey,
            ),
            date=datetime(2019, 12, 11, 3, 50, 55, 0, timezone.utc),
        )
        signed = await sign(
            document=DOC_TEMPLATE_2020,
            suite=suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert signed == DOC_SIGNED_2020

    async def test_verify_Ed25519Signature2018(self):
        # Verification requires lot less input parameters
        suite = Ed25519Signature2018(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=ED25519),
        )

        result = await verify(
            document=DOC_SIGNED,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result == DOC_VERIFIED

    async def test_verify_Ed25519Signature2020(self):
        # Verification requires lot less input parameters
        suite = Ed25519Signature2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=ED25519),
        )

        result = await verify(
            document=DOC_SIGNED_2020,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result == DOC_VERIFIED_2020

    @pytest.mark.ursa_bbs_signatures
    async def test_sign_BbsBlsSignature2020(self):
        # Use different key pair and suite for signing and verification
        # as during verification a lot of information can be extracted
        # from the proof / document
        suite = BbsBlsSignature2020(
            verification_method=self.bls12381g2_verification_method,
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=BLS12381G2,
                public_key_base58=self.bls12381g2_key_info.verkey,
            ),
            date=datetime(2019, 12, 11, 3, 50, 55, 0),
        )
        signed = await sign(
            document=DOC_TEMPLATE_BBS,
            suite=suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        # BBS generates unique signature every time so we cant compare signatures
        assert signed

        result = await verify(
            document=signed,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    @pytest.mark.ursa_bbs_signatures
    async def test_verify_BbsBlsSignature2020(self):
        # Verification requires lot less input parameters
        suite = BbsBlsSignature2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2),
        )

        result = await verify(
            document=DOC_SIGNED_BBS,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    @pytest.mark.ursa_bbs_signatures
    async def test_derive_BbsBlsSignatureProof2020(self):
        # Verification requires lot less input parameters
        suite = BbsBlsSignatureProof2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2),
        )

        result = await derive(
            document=DOC_SIGNED_BBS,
            reveal_document=DOC_FRAME_BBS,
            suite=suite,
            document_loader=custom_document_loader,
        )

        assert result

    @pytest.mark.ursa_bbs_signatures
    async def test_verify_BbsBlsSignatureProof2020(self):
        # Verification requires lot less input parameters
        suite = BbsBlsSignatureProof2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2),
        )

        result = await verify(
            document=DOC_DERIVED_BBS,
            suites=[suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified
