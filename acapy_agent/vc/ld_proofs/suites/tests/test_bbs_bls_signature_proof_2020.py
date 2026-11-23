from unittest import IsolatedAsyncioTestCase, mock

import pytest

from .....did.did_key import DIDKey
from .....utils.testing import create_test_profile
from .....wallet.base import BaseWallet
from .....wallet.key_type import BLS12381G2
from ....tests.data import (
    TEST_LD_DOCUMENT_BAD_PARTIAL_PROOF_BBS,
    TEST_LD_DOCUMENT_PARTIAL_PROOF_BBS,
    TEST_LD_DOCUMENT_PROOF_BBS,
    TEST_LD_DOCUMENT_REVEAL,
    TEST_LD_DOCUMENT_REVEAL_ALL,
    TEST_LD_DOCUMENT_SIGNED_BBS,
    TEST_VC_DOCUMENT_NESTED_PARTIAL_PROOF_BBS,
    TEST_VC_DOCUMENT_NESTED_PROOF_BBS,
    TEST_VC_DOCUMENT_NESTED_REVEAL,
    TEST_VC_DOCUMENT_NESTED_SIGNED_BBS,
    TEST_VC_DOCUMENT_PARTIAL_PROOF_BBS,
    TEST_VC_DOCUMENT_REVEAL,
    TEST_VC_DOCUMENT_SIGNED_BBS,
)
from ....tests.document_loader import custom_document_loader
from ....vc_ld import derive_credential, verify_credential
from ...crypto.wallet_key_pair import WalletKeyPair
from ...error import LinkedDataProofException
from ...ld_proofs import derive, sign, verify
from ...purposes.assertion_proof_purpose import AssertionProofPurpose
from ..bbs_bls_signature_2020 import BbsBlsSignature2020
from ..bbs_bls_signature_proof_2020 import BbsBlsSignatureProof2020


@pytest.mark.ursa_bbs_signatures
class TestBbsBlsSignatureProof2020(IsolatedAsyncioTestCase):
    test_seed = "testseed000000000000000000000001"

    async def asyncSetUp(self):
        self.profile = await create_test_profile()
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            self.key = await wallet.create_signing_key(
                key_type=BLS12381G2, seed=self.test_seed
            )
        self.verification_method = DIDKey.from_public_key_b58(
            self.key.verkey, BLS12381G2
        ).key_id

        self.key_pair = WalletKeyPair(profile=self.profile, key_type=BLS12381G2)

    async def test_derive_ld_proofs(self):
        derived = await derive(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_LD_DOCUMENT_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_verify_derived_x_bad_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_PARTIAL_PROOF_BBS,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert not result.verified

    async def test_derive_x_unsigned_claims(self):
        doc = {**TEST_LD_DOCUMENT_SIGNED_BBS, "unsigned_claim": True}

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_x_modified_claims(self):
        doc = {**TEST_LD_DOCUMENT_SIGNED_BBS, "email": "bad@example.com"}

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_x_removed_claims(self):
        doc = TEST_LD_DOCUMENT_SIGNED_BBS.copy()
        doc.pop("email")

        with self.assertRaises(Exception) as context:
            await derive(
                document=doc,
                reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
                document_loader=custom_document_loader,
                suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
            )
        assert "The messages and signature do not match" in str(context.exception)

    async def test_derive_ld_proofs_reveal_all(self):
        derived = await derive(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_LD_DOCUMENT_REVEAL_ALL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_derive_vc(self):
        derived = await derive_credential(
            credential=TEST_VC_DOCUMENT_SIGNED_BBS,
            reveal_document=TEST_VC_DOCUMENT_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_derive_vc_nested(self):
        derived = await derive_credential(
            credential=TEST_VC_DOCUMENT_NESTED_SIGNED_BBS,
            reveal_document=TEST_VC_DOCUMENT_NESTED_REVEAL,
            document_loader=custom_document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

        assert derived

    async def test_verify_ld_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_partial_ld_proof(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_nested_vc_full_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_NESTED_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_nested_vc_partial_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_NESTED_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_verify_derived_vc_partial_reveal(self):
        result = await verify_credential(
            credential=TEST_VC_DOCUMENT_PARTIAL_PROOF_BBS,
            purpose=AssertionProofPurpose(),
            document_loader=custom_document_loader,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
        )

        assert result.verified

    async def test_derive_proof_x_invalid_proof_type(self):
        suite = BbsBlsSignatureProof2020(
            key_pair=self.key_pair,
        )

        with self.assertRaises(LinkedDataProofException):
            await suite.derive_proof(
                reveal_document=mock.MagicMock(),
                document=mock.MagicMock(),
                proof={"type": "incorrect type"},
                document_loader=mock.MagicMock(),
            )

    def _document_loader(self, url: str, options: dict):
        """Resolve the signing key's did:key, and other documents from test data."""
        did_key = DIDKey.from_public_key_b58(self.key.verkey, BLS12381G2)
        if url.split("#")[0] == did_key.did:
            return {
                "contentType": "application/ld+json",
                "contextUrl": None,
                "document": did_key.did_doc,
                "documentUrl": url,
            }
        return custom_document_loader(url, options)

    async def _sign_and_derive(self, first_name: str):
        """Sign a document with the given firstName, then derive a proof."""
        document = {
            "@context": ["http://schema.org/", "https://w3id.org/security/bbs/v1"],
            "@type": "Person",
            "firstName": first_name,
            "lastName": "Does",
            "url": "https://example.com/_:c14n0",
        }
        signed = await sign(
            document=document,
            suite=BbsBlsSignature2020(
                key_pair=WalletKeyPair(
                    profile=self.profile,
                    key_type=BLS12381G2,
                    public_key_base58=self.key.verkey,
                ),
                verification_method=self.verification_method,
            ),
            document_loader=self._document_loader,
            purpose=AssertionProofPurpose(),
        )
        return await derive(
            document=signed,
            reveal_document={
                "@context": ["http://schema.org/", "https://w3id.org/security/bbs/v1"],
                "@type": "Person",
                "@explicit": True,
                "firstName": {},
                "url": {},
            },
            document_loader=self._document_loader,
            suite=BbsBlsSignatureProof2020(key_pair=self.key_pair),
        )

    async def _verify(self, document):
        return await verify(
            document=document,
            suites=[BbsBlsSignatureProof2020(key_pair=self.key_pair)],
            document_loader=self._document_loader,
            purpose=AssertionProofPurpose(),
        )

    async def test_derive_and_verify_blank_node_label_in_values(self):
        for first_name in ("_:c14n0", "<urn:bnid:_:c14n0>", "a _:c14n12 b"):
            with self.subTest(first_name=first_name):
                derived = await self._sign_and_derive(first_name)

                assert derived["firstName"] == first_name
                assert derived["url"] == "https://example.com/_:c14n0"
                assert (await self._verify(derived)).verified

    async def test_verify_derived_x_blank_node_label_value_changed(self):
        cases = [
            ("_:c14n0", "<urn:bnid:_:c14n0>"),
            ("<urn:bnid:_:c14n0>", "_:c14n0"),
        ]
        for signed_value, presented_value in cases:
            with self.subTest(signed_value=signed_value):
                derived = await self._sign_and_derive(signed_value)

                assert not (
                    await self._verify({**derived, "firstName": presented_value})
                ).verified

    def test_transform_blank_node_ids_only_rewrites_terms(self):
        suite = BbsBlsSignatureProof2020(key_pair=self.key_pair)
        statements = [
            '_:c14n0 <http://schema.org/name> "_:c14n1 \\" _:c14n2" .',
            "_:c14n0 <http://schema.org/url> <https://example.com/_:c14n0> .",
            "_:c14n0 <http://schema.org/knows> _:c14n10 _:c14n1 .",
        ]
        placeholders = [
            '<urn:bnid:_:c14n0> <http://schema.org/name> "_:c14n1 \\" _:c14n2" .',
            "<urn:bnid:_:c14n0> <http://schema.org/url> <https://example.com/_:c14n0> .",
            "<urn:bnid:_:c14n0> <http://schema.org/knows> <urn:bnid:_:c14n10> "
            "<urn:bnid:_:c14n1> .",
        ]

        assert (
            suite._transform_blank_node_ids_into_placeholder_node_ids(statements)
            == placeholders
        )
        assert (
            suite._transform_placeholder_node_ids_into_blank_node_ids(placeholders)
            == statements
        )
        literal = '_:c14n0 <http://schema.org/name> "<urn:bnid:_:c14n1>" .'
        assert suite._transform_placeholder_node_ids_into_blank_node_ids([literal]) == [
            literal
        ]
