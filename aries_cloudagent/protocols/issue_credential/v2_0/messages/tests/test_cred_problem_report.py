import pytest

from unittest import mock
from unittest import TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..cred_problem_report import (
    V20CredProblemReport,
    V20CredProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)

from .. import cred_problem_report as test_module


class TestCredProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = V20CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        assert prob._type == DIDCommPrefix.qualify_current(CRED_20_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V20CredProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = V20CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )

        prob = V20CredProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V20CredProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = V20CredProblemReport(
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

        prob = V20CredProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ISSUANCE_ABANDONED.value,
            }
        )
        data = prob.serialize()
        model_instance = V20CredProblemReport.deserialize(data)
        assert isinstance(model_instance, V20CredProblemReport)

        prob = V20CredProblemReport()
        data = prob.serialize()
        with pytest.raises(BaseModelError):
            V20CredProblemReport.deserialize(data)

    def test_validate_and_logger(self):
        """Capture ValidationError and Logs."""
        data = V20CredProblemReport(
            description={
                "en": "Insufficient credit",
                "code": "invalid_code",
            },
        ).serialize()
        with mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger:
            V20CredProblemReportSchema().validate_fields(data)
        assert mock_logger.warning.call_count == 1

    def test_validate_x(self):
        """Exercise validation requirements."""
        schema = V20CredProblemReportSchema()
        with pytest.raises(ValidationError):
            schema.validate_fields({})
