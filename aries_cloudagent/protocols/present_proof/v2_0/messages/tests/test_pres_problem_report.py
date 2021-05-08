import pytest

from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PRES_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..pres_problem_report import V20PresProblemReport, ProblemReportReason


class TestV20PresProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = V20PresProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ABANDONED.value,
            }
        )
        assert prob._type == DIDCommPrefix.qualify_current(PRES_20_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.pres_problem_report."
        "V20PresProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = V20PresProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ABANDONED.value,
            }
        )

        prob = V20PresProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.pres_problem_report."
        "V20PresProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = V20PresProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ABANDONED.value,
            }
        )

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = V20PresProblemReport(
            description={
                "en": "oh no",
                "code": ProblemReportReason.ABANDONED.value,
            }
        )
        data = prob.serialize()
        model_instance = V20PresProblemReport.deserialize(data)
        assert isinstance(model_instance, V20PresProblemReport)

        prob = V20PresProblemReport()
        data = prob.serialize()
        with pytest.raises(BaseModelError):
            V20PresProblemReport.deserialize(data)
