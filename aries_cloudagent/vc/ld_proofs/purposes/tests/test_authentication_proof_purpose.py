from datetime import datetime, timedelta
from asynctest import TestCase, mock as async_mock

from ...validation_result import PurposeResult
from ..controller_proof_purpose import ControllerProofPurpose
from ..authentication_proof_purpose import AuthenticationProofPurpose


class TestAuthenticationProofPurpose(TestCase):
    async def test_properties(self):
        date = datetime.now()
        delta = timedelta(1)
        challenge = "challenge"
        domain = "domain"
        proof_purpose = AuthenticationProofPurpose(
            challenge=challenge, domain=domain, date=date, max_timestamp_delta=delta
        )
        proof_purpose2 = AuthenticationProofPurpose(
            challenge=challenge, domain=domain, date=date, max_timestamp_delta=delta
        )

        assert proof_purpose.term == "authentication"
        assert proof_purpose.date == date
        assert proof_purpose.max_timestamp_delta == delta
        assert proof_purpose.challenge == challenge
        assert proof_purpose.domain == domain

        assert proof_purpose2 == proof_purpose
        assert proof_purpose != 10

    async def test_validate(self):
        proof_purpose = AuthenticationProofPurpose(
            challenge="8378c56e-4926-4a54-9587-0f2ef564619a", domain="example.com"
        )

        with async_mock.patch.object(
            ControllerProofPurpose, "validate"
        ) as validate_mock:
            validate_mock.return_value = PurposeResult(valid=True)
            proof = {
                "challenge": "8378c56e-4926-4a54-9587-0f2ef564619a",
                "domain": "example.com",
            }
            document = async_mock.MagicMock()
            suite = async_mock.MagicMock()
            verification_method = {"controller": "controller"}
            document_loader = async_mock.MagicMock()

            result = proof_purpose.validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )
            validate_mock.assert_called_once_with(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )
            assert result.valid

    async def test_validate_x_challenge_does_not_match(self):
        proof_purpose = AuthenticationProofPurpose(
            challenge="8378c56e-4926-4a54-9587-0f2ef564619a", domain="example.com"
        )

        with async_mock.patch.object(
            ControllerProofPurpose, "validate"
        ) as validate_mock:
            validate_mock.return_value = PurposeResult(valid=True)

            result = proof_purpose.validate(
                proof={
                    "challenge": "another8378c56e-4926-4a54-9587-0f2ef564619a",
                    "domain": "example.com",
                },
                document=async_mock.MagicMock(),
                suite=async_mock.MagicMock(),
                verification_method=async_mock.MagicMock(),
                document_loader=async_mock.MagicMock(),
            )
            assert not result.valid
            assert "The challenge is not as expected" in str(result.error)

    async def test_validate_x_domain_does_not_match(self):
        proof_purpose = AuthenticationProofPurpose(
            challenge="8378c56e-4926-4a54-9587-0f2ef564619a", domain="example.com"
        )

        with async_mock.patch.object(
            ControllerProofPurpose, "validate"
        ) as validate_mock:
            validate_mock.return_value = PurposeResult(valid=True)

            result = proof_purpose.validate(
                proof={
                    "challenge": "8378c56e-4926-4a54-9587-0f2ef564619a",
                    "domain": "anotherexample.com",
                },
                document=async_mock.MagicMock(),
                suite=async_mock.MagicMock(),
                verification_method=async_mock.MagicMock(),
                document_loader=async_mock.MagicMock(),
            )
            assert not result.valid
            assert "The domain is not as expected" in str(result.error)

    async def test_update(self):
        proof_purpose = AuthenticationProofPurpose(
            challenge="8378c56e-4926-4a54-9587-0f2ef564619a", domain="example.com"
        )

        proof = {}
        ret_proof = proof_purpose.update(proof)

        assert proof == ret_proof
        assert proof.get("challenge") == "8378c56e-4926-4a54-9587-0f2ef564619a"
        assert proof.get("domain") == "example.com"
