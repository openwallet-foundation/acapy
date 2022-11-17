from asynctest import TestCase
import pytest

from ...wallet.key_type import BLS12381G2
from ...wallet.util import b58_to_bytes
from ...wallet.in_memory import InMemoryWallet
from ...core.in_memory import InMemoryProfile
from ..ld_proofs import (
    WalletKeyPair,
    AssertionProofPurpose,
    verify,
    sign,
    derive,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
)
from .document_loader import custom_document_loader
from .data import (
    BBS_PARTIAL_PROOF_NESTED_VC_MATTR,
    BBS_VC_MATTR,
    BBS_NESTED_VC_MATTR,
    BBS_VC_REVEAL_DOCUMENT_MATTR,
    BBS_PARTIAL_PROOF_VC_MATTR,
    BBS_PROOF_NESTED_VC_MATTR,
    BBS_PROOF_VC_MATTR,
    BBS_SIGNED_NESTED_VC_MATTR,
    BBS_SIGNED_VC_MATTR,
    BBS_NESTED_VC_REVEAL_DOCUMENT_MATTR,
    BBS_NESTED_VC_FULL_REVEAL_DOCUMENT_MATTR,
)


@pytest.mark.ursa_bbs_signatures
class TestBbsMattrInterop(TestCase):
    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)

        # Manually add key as we only have the private key, no seed (from mattr bbs repo)
        private_key_base58 = "5D6Pa8dSwApdnfg7EZR8WnGfvLDCZPZGsZ5Y1ELL9VDj"
        public_key_base58 = "oqpWYKaZD9M1Kbe94BVXpr8WTdFBNZyKv48cziTiQUeuhm7sBhCABMyYG4kcMrseC68YTFFgyhiNeBKjzdKk9MiRWuLv5H4FFujQsQK2KTAtzU8qTBiZqBHMmnLF4PL7Ytu"
        self.profile.keys[public_key_base58] = {
            # we don't have the seed
            "seed": "seed",
            "secret": b58_to_bytes(private_key_base58),
            "verkey": public_key_base58,
            "metadata": {},
            "key_type": BLS12381G2,
        }

        self.signature_issuer_suite = BbsBlsSignature2020(
            verification_method="did:example:489398593#test",
            key_pair=WalletKeyPair(
                wallet=self.wallet,
                key_type=BLS12381G2,
                public_key_base58=public_key_base58,
            ),
        )

        self.signature_suite = BbsBlsSignature2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2),
        )
        self.proof_suite = BbsBlsSignatureProof2020(
            key_pair=WalletKeyPair(wallet=self.wallet, key_type=BLS12381G2)
        )

    async def test_sign_bbs_vc_mattr(self):
        # TODO: ideally we verify the resulting document with the
        # MATTR bbs-jsonld lib. This is now manually done.
        signed = await sign(
            document=BBS_VC_MATTR,
            suite=self.signature_issuer_suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert signed

    async def test_sign_bbs_nested_vc_mattr(self):
        # TODO: ideally we verify the resulting document with the
        # MATTR bbs-jsonld lib. This is now manually done.
        signed = await sign(
            document=BBS_NESTED_VC_MATTR,
            suite=self.signature_issuer_suite,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert signed

    async def test_verify_bbs_signed_vc_mattr(self):
        result = await verify(
            document=BBS_SIGNED_VC_MATTR,
            suites=[self.signature_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_verify_bbs_signed_nested_vc_mattr(self):
        result = await verify(
            document=BBS_SIGNED_NESTED_VC_MATTR,
            suites=[self.signature_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_derive_bbs_proof_vc_mattr(self):
        # TODO: ideally we verify the resulting document with the
        # MATTR bbs-jsonld lib. This is now manually done.
        derived = await derive(
            document=BBS_SIGNED_VC_MATTR,
            reveal_document=BBS_VC_REVEAL_DOCUMENT_MATTR,
            suite=self.proof_suite,
            document_loader=custom_document_loader,
        )

        assert derived

    async def test_derive_full_bbs_proof_nested_vc_mattr(self):
        # TODO: ideally we verify the resulting document with the
        # MATTR bbs-jsonld lib. This is now manually done.
        derived = await derive(
            document=BBS_SIGNED_NESTED_VC_MATTR,
            reveal_document=BBS_NESTED_VC_FULL_REVEAL_DOCUMENT_MATTR,
            suite=self.proof_suite,
            document_loader=custom_document_loader,
        )

        assert derived

    async def test_derive_partial_bbs_proof_nested_vc_mattr(self):
        # TODO: ideally we verify the resulting document with the
        # MATTR bbs-jsonld lib. This is now manually done.
        derived = await derive(
            document=BBS_SIGNED_NESTED_VC_MATTR,
            reveal_document=BBS_NESTED_VC_REVEAL_DOCUMENT_MATTR,
            suite=self.proof_suite,
            document_loader=custom_document_loader,
        )

        assert derived

    async def test_verify_bbs_proof_vc_mattr(self):
        # BBS full proof, no subject nesting
        result = await verify(
            document=BBS_PROOF_VC_MATTR,
            suites=[self.proof_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_verify_bbs_partial_proof_vc_mattr(self):
        # BBS partial proof, no subject nesting
        result = await verify(
            document=BBS_PARTIAL_PROOF_VC_MATTR,
            suites=[self.proof_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_verify_bbs_proof_nested_vc_mattr(self):
        # BBS full proof nested vc
        result = await verify(
            document=BBS_PROOF_NESTED_VC_MATTR,
            suites=[self.proof_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified

    async def test_verify_bbs_partial_proof_nested_vc_mattr(self):
        # BBS partial proof nested vc
        result = await verify(
            document=BBS_PARTIAL_PROOF_NESTED_VC_MATTR,
            suites=[self.proof_suite],
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
        )

        assert result.verified
