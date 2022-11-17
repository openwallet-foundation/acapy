import logging
import pytest

from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_30_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..cred_problem_report import (
    V30CredProblemReport,
    V30CredProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)


class TestCredProblemReport(TestCase):
    """Problem report tests."""

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def test_init_type(self):
        """Test initializer."""

        prob = V30CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        assert prob._type == DIDCommPrefix.qualify_current(CRED_30_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V30CredProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = V30CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )

        prob = V30CredProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V30CredProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = V30CredProblemReport(
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

        prob = V30CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        data = prob.serialize()
        model_instance = V30CredProblemReport.deserialize(data)
        assert isinstance(model_instance, V30CredProblemReport)

        prob = V30CredProblemReport()
        data = prob.serialize()
        with pytest.raises(BaseModelError):
            V30CredProblemReport.deserialize(data)

    def test_validate_and_logger(self):
        """Capture ValidationError and Logs."""
        data = V30CredProblemReport(
            description={
                "en": "Insufficient credit",
                "code": "invalid_code",
            },
        ).serialize()
        self._caplog.set_level(logging.WARNING)
        V30CredProblemReportSchema().validate_fields(data)
        assert "Unexpected error code received" in self._caplog.text

    def test_validate_x(self):
        """Exercise validation requirements."""
        schema = V30CredProblemReportSchema()
        with pytest.raises(ValidationError):
            schema.validate_fields({})
