import logging
import pytest

from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CREDENTIAL_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..credential_problem_report import (
    CredentialProblemReport,
    CredentialProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)


class TestCredentialProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = CredentialProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        assert prob._type == DIDCommPrefix.qualify_current(CREDENTIAL_PROBLEM_REPORT)

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "CredentialProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = CredentialProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )

        prob = CredentialProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "CredentialProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = CredentialProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = CredentialProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        data = prob.serialize()
        model_instance = CredentialProblemReport.deserialize(data)
        assert isinstance(model_instance, CredentialProblemReport)

        prob = CredentialProblemReport()
        data = prob.serialize()
        with pytest.raises(BaseModelError):
            CredentialProblemReport.deserialize(data)

    def test_validate_x(self):
        """Exercise validation requirements."""
        schema = CredentialProblemReportSchema()
        with pytest.raises(ValidationError):
            schema.validate_fields({})

    def test_validate_and_logger(self):
        """Capture ValidationError and Logs."""
        data = CredentialProblemReport(
            description={
                "en": "oh no",
                "code": "invalid_code",
            },
        ).serialize()
        self._caplog.set_level(logging.WARNING)
        CredentialProblemReportSchema().validate_fields(data)
        assert "Unexpected error code received" in self._caplog.text
