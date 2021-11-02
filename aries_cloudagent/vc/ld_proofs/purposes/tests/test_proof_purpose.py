from datetime import datetime, timedelta
from asynctest import TestCase, mock as async_mock

from .....messaging.util import datetime_to_str
from ..proof_purpose import ProofPurpose


class TestProofPurpose(TestCase):
    async def test_properties(self):
        term = "TestTerm"
        date = datetime.now()
        delta = timedelta(1)
        proof_purpose = ProofPurpose(term=term, date=date, max_timestamp_delta=delta)
        proof_purpose2 = ProofPurpose(term=term, date=date, max_timestamp_delta=delta)

        assert proof_purpose.term == term
        assert proof_purpose.date == date
        assert proof_purpose.max_timestamp_delta == delta

        assert proof_purpose2 == proof_purpose
        assert proof_purpose != 10

    async def test_validate(self):
        proof_purpose = ProofPurpose(term="ProofTerm", date=datetime.now())

        result = proof_purpose.validate(
            proof=async_mock.MagicMock(),
            document=async_mock.MagicMock(),
            suite=async_mock.MagicMock(),
            verification_method=async_mock.MagicMock(),
            document_loader=async_mock.MagicMock(),
        )
        assert result.valid

    async def test_validate_timestamp_delta(self):
        date = datetime.now()
        proof_purpose = ProofPurpose(
            term="ProofTerm", date=date, max_timestamp_delta=timedelta(10)
        )

        result = proof_purpose.validate(
            proof={"created": datetime_to_str(date + timedelta(5))},
            document=async_mock.MagicMock(),
            suite=async_mock.MagicMock(),
            verification_method=async_mock.MagicMock(),
            document_loader=async_mock.MagicMock(),
        )
        assert result.valid

    async def test_validate_timestamp_delta_out_of_rage(self):
        date = datetime.now()
        proof_purpose = ProofPurpose(
            term="ProofTerm", date=date, max_timestamp_delta=timedelta(10)
        )

        result = proof_purpose.validate(
            proof={"created": datetime_to_str(date + timedelta(15))},
            document=async_mock.MagicMock(),
            suite=async_mock.MagicMock(),
            verification_method=async_mock.MagicMock(),
            document_loader=async_mock.MagicMock(),
        )

        assert not result.valid
