from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest import mock

from ...validation_result import PurposeResult
from ..assertion_proof_purpose import AssertionProofPurpose
from ..credential_issuance_purpose import CredentialIssuancePurpose
from ....tests.data import TEST_VC_DOCUMENT_SIGNED_ED25519
from ....tests.document_loader import custom_document_loader


class TestCredentialIssuancePurpose(IsolatedAsyncioTestCase):
    async def test_properties(self):
        date = datetime.now()
        delta = timedelta(1)
        proof_purpose = CredentialIssuancePurpose(date=date, max_timestamp_delta=delta)
        proof_purpose2 = CredentialIssuancePurpose(date=date, max_timestamp_delta=delta)

        assert proof_purpose.term == "assertionMethod"
        assert proof_purpose.date == date
        assert proof_purpose.max_timestamp_delta == delta

        assert proof_purpose2 == proof_purpose
        assert proof_purpose != 10

    async def test_validate(self):
        proof_purpose = CredentialIssuancePurpose()

        with mock.patch.object(AssertionProofPurpose, "validate") as validate_mock:
            validate_mock.return_value = PurposeResult(
                valid=True, controller={"id": TEST_VC_DOCUMENT_SIGNED_ED25519["issuer"]}
            )
            document = TEST_VC_DOCUMENT_SIGNED_ED25519.copy()
            proof = document.pop("proof")
            suite = mock.MagicMock()
            verification_method = {"controller": "controller"}

            result = proof_purpose.validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=custom_document_loader,
            )
            validate_mock.assert_called_once_with(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=custom_document_loader,
            )
            assert result.valid

    async def test_validate_x_no_issuer(self):
        proof_purpose = CredentialIssuancePurpose()

        with mock.patch.object(AssertionProofPurpose, "validate") as validate_mock:
            validate_mock.return_value = PurposeResult(
                valid=True, controller={"id": TEST_VC_DOCUMENT_SIGNED_ED25519["issuer"]}
            )
            document = TEST_VC_DOCUMENT_SIGNED_ED25519.copy()
            document.pop("issuer")
            proof = document.pop("proof")
            suite = mock.MagicMock()
            verification_method = {"controller": "controller"}

            result = proof_purpose.validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=custom_document_loader,
            )
            assert not result.valid
            assert "issuer is required" in str(result.error)

    async def test_validate_x_no_match_issuer(self):
        proof_purpose = CredentialIssuancePurpose()

        with mock.patch.object(AssertionProofPurpose, "validate") as validate_mock:
            validate_mock.return_value = PurposeResult(
                valid=True, controller={"id": "random_controller_id"}
            )
            document = TEST_VC_DOCUMENT_SIGNED_ED25519.copy()
            proof = document.pop("proof")
            suite = mock.MagicMock()
            verification_method = {"controller": "controller"}

            result = proof_purpose.validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=custom_document_loader,
            )
            assert not result.valid
            assert "issuer must match the verification method controller" in str(
                result.error
            )

    async def test_validate_x_super_invalid(self):
        proof_purpose = CredentialIssuancePurpose()

        with mock.patch.object(AssertionProofPurpose, "validate") as validate_mock:
            validate_mock.return_value = mock.MagicMock(valid=False)

            result = proof_purpose.validate(
                proof=mock.MagicMock(),
                document=mock.MagicMock(),
                suite=mock.MagicMock(),
                verification_method=mock.MagicMock(),
                document_loader=mock.MagicMock(),
            )

            assert not result.valid
            assert result == validate_mock.return_value
