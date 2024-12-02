from unittest import IsolatedAsyncioTestCase

import pytest

from ...utils.testing import create_test_profile
from ...wallet.base import BaseWallet
from ...wallet.key_type import BLS12381G2
from ..ld_proofs import (
    AssertionProofPurpose,
    BbsBlsSignature2020,
    BbsBlsSignatureProof2020,
    WalletKeyPair,
    derive,
    sign,
    verify,
)
from .data import (
    BBS_NESTED_VC_FULL_REVEAL_DOCUMENT_MATTR,
    BBS_NESTED_VC_MATTR,
    BBS_NESTED_VC_REVEAL_DOCUMENT_MATTR,
    BBS_PARTIAL_PROOF_NESTED_VC_MATTR,
    BBS_PARTIAL_PROOF_VC_MATTR,
    BBS_PROOF_NESTED_VC_MATTR,
    BBS_PROOF_VC_MATTR,
    BBS_SIGNED_NESTED_VC_MATTR,
    BBS_SIGNED_VC_MATTR,
    BBS_VC_MATTR,
    BBS_VC_REVEAL_DOCUMENT_MATTR,
)
from .document_loader import custom_document_loader


@pytest.mark.ursa_bbs_signatures
class TestBbsMattrInterop(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            key_info = await wallet.create_key(
                key_type=BLS12381G2,
            )

        self.signature_issuer_suite = BbsBlsSignature2020(
            verification_method="did:example:489398593#test",
            key_pair=WalletKeyPair(
                profile=self.profile,
                key_type=BLS12381G2,
                public_key_base58=key_info.verkey,
            ),
        )

        self.signature_suite = BbsBlsSignature2020(
            key_pair=WalletKeyPair(profile=self.profile, key_type=BLS12381G2),
        )
        self.proof_suite = BbsBlsSignatureProof2020(
            key_pair=WalletKeyPair(profile=self.profile, key_type=BLS12381G2)
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
