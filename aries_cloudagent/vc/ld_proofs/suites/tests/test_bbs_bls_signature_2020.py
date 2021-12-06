from asynctest import TestCase, mock as async_mock
import pytest

from .....did.did_key import DIDKey
from .....wallet.key_pair import KeyType
from .....wallet.in_memory import InMemoryWallet
from .....core.in_memory import InMemoryProfile
from ....tests.document_loader import custom_document_loader
from ....tests.data import (
    TEST_LD_DOCUMENT,
    TEST_LD_DOCUMENT_SIGNED_BBS,
    TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
    TEST_VC_DOCUMENT,
    TEST_VC_DOCUMENT_SIGNED_BBS,
)

from ...error import LinkedDataProofException
from ...crypto.wallet_key_pair import WalletKeyPair
from ...purposes.assertion_proof_purpose import AssertionProofPurpose
from ...ld_proofs import sign, verify

from ..bbs_bls_signature_2020 import BbsBlsSignature2020

TEST_CRED_WITH_CRED_SCHEMA = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://w3id.org/citizenship/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "type": ["VerifiableCredential", "PermanentResident"],
    "id": "https://credential.example.com/residents/1234567890",
    "issuer": "did:key:zUC7D5oH6hfJr96qZsU8r3XhwiN8BwhWpddV4pfDeKo4YyCDfLa7niUtGcEStMNGRAFyUbtxQfYVpzUN1ErpstFNNxiLQrFdGPD5XSHYqXTZP3xHuRxFyFP4DicuPdY7a6pQTxw",
    "issuanceDate": "2020-01-01T12:00:00Z",
    "credentialSchema": {
        "id": "https://example.com/schema",
        "type": "JsonSchemaValidator2020",
    },
    "credentialSubject": {
        "id": "did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT",
        "type": ["PermanentResident"],
        "givenName": "ALICE",
        "familyName": "SMITH",
        "gender": "Female",
        "birthCountry": "Bahamas",
        "birthDate": "1958-07-17",
    },
}

EXPECTED_DOCUMENT_STATEMENTS = [
    '<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <http://schema.org/birthDate> "1958-07-17"^^<http://www.w3.org/2001/XMLSchema#dateTime> .',
    '<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <http://schema.org/familyName> "SMITH" .',
    '<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <http://schema.org/gender> "Female" .',
    '<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <http://schema.org/givenName> "ALICE" .',
    "<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/citizenship#PermanentResident> .",
    '<did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> <https://w3id.org/citizenship#birthCountry> "Bahamas" .',
    "<https://credential.example.com/residents/1234567890> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://w3id.org/citizenship#PermanentResident> .",
    "<https://credential.example.com/residents/1234567890> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://www.w3.org/2018/credentials#VerifiableCredential> .",
    "<https://credential.example.com/residents/1234567890> <https://www.w3.org/2018/credentials#credentialSchema> <https://example.com/schema> .",
    "<https://credential.example.com/residents/1234567890> <https://www.w3.org/2018/credentials#credentialSubject> <did:key:zUC71RG7iRDx8JmAciZmn4dWR5NGBRHaPAKrLzD2dmoaTWUzViJui6L3RZbQHVgtsQbcERzZUe1Vk6Khym6vpZqfXVXNLcdhgeuKDB4wHU5Fr1iX76jqjGVd7n7D7cRn2AFq8cT> .",
    '<https://credential.example.com/residents/1234567890> <https://www.w3.org/2018/credentials#issuanceDate> "2020-01-01T12:00:00Z"^^<http://www.w3.org/2001/XMLSchema#dateTime> .',
    "<https://credential.example.com/residents/1234567890> <https://www.w3.org/2018/credentials#issuer> <did:key:zUC7D5oH6hfJr96qZsU8r3XhwiN8BwhWpddV4pfDeKo4YyCDfLa7niUtGcEStMNGRAFyUbtxQfYVpzUN1ErpstFNNxiLQrFdGPD5XSHYqXTZP3xHuRxFyFP4DicuPdY7a6pQTxw> .",
    "<https://example.com/schema> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <https://json-ld.org/playground/JsonSchemaValidator2020> .",
]


@pytest.mark.ursa_bbs_signatures
class TestBbsBlsSignature2020(TestCase):
    test_seed = "testseed000000000000000000000001"

    async def setUp(self):
        self.profile = InMemoryProfile.test_profile()
        self.wallet = InMemoryWallet(self.profile)
        self.key = await self.wallet.create_signing_key(
            key_type=KeyType.BLS12381G2, seed=self.test_seed
        )
        self.verification_method = DIDKey.from_public_key_b58(
            self.key.verkey, KeyType.BLS12381G2
        ).key_id

        self.sign_key_pair = WalletKeyPair(
            wallet=self.wallet,
            key_type=KeyType.BLS12381G2,
            public_key_base58=self.key.verkey,
        )
        self.verify_key_pair = WalletKeyPair(
            wallet=self.wallet, key_type=KeyType.BLS12381G2
        )

    async def test_create_verify_document_data(self):
        suite = BbsBlsSignature2020(
            key_pair=self.sign_key_pair,
            verification_method=self.verification_method,
        )
        gen_doc_stms = suite._create_verify_document_data(
            document=TEST_CRED_WITH_CRED_SCHEMA, document_loader=custom_document_loader
        )
        assert len(gen_doc_stms) == len(EXPECTED_DOCUMENT_STATEMENTS)

    async def test_sign_ld_proofs(self):
        signed = await sign(
            document=TEST_LD_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_ld_proofs(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_ld_proofs_not_verified_bad_signature(self):
        result = await verify(
            document=TEST_LD_DOCUMENT_BAD_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_unsigned_statement(self):
        MODIFIED_DOCUMENT = {**TEST_LD_DOCUMENT_SIGNED_BBS, "unsigned_claim": "oops"}
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_verify_ld_proofs_not_verified_changed_statement(self):
        MODIFIED_DOCUMENT = {
            **TEST_LD_DOCUMENT_SIGNED_BBS,
            "email": "someOtherEmail@example.com",
        }
        result = await verify(
            document=MODIFIED_DOCUMENT,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert not result.verified

    async def test_sign_vc(self):
        signed = await sign(
            document=TEST_VC_DOCUMENT,
            suite=BbsBlsSignature2020(
                key_pair=self.sign_key_pair,
                verification_method=self.verification_method,
            ),
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert signed

    async def test_verify_vc(self):
        result = await verify(
            document=TEST_VC_DOCUMENT_SIGNED_BBS,
            suites=[BbsBlsSignature2020(key_pair=self.verify_key_pair)],
            document_loader=custom_document_loader,
            purpose=AssertionProofPurpose(),
        )

        assert result
        assert result.verified

    async def test_verify_signature_x_invalid_proof_value(self):
        suite = BbsBlsSignature2020(
            key_pair=self.sign_key_pair,
            verification_method=self.verification_method,
        )

        with self.assertRaises(LinkedDataProofException):
            await suite.verify_signature(
                verify_data=async_mock.MagicMock(),
                verification_method=async_mock.MagicMock(),
                document=async_mock.MagicMock(),
                proof={"proofValue": {"not": "a string"}},
                document_loader=async_mock.MagicMock(),
            )
