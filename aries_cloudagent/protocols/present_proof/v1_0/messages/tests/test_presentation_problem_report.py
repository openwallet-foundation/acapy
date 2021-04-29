from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import PRESENTATION_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..presentation_problem_report import PresentationProblemReport


class TestPresentationProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = PresentationProblemReport()
        assert prob._type == DIDCommPrefix.qualify_current(PRESENTATION_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.presentation_problem_report."
        "PresentationProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = PresentationProblemReport()

        prob = PresentationProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.presentation_problem_report."
        "PresentationProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = PresentationProblemReport()

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = PresentationProblemReport()
        data = prob.serialize()
        model_instance = PresentationProblemReport.deserialize(data)
        assert isinstance(model_instance, PresentationProblemReport)
