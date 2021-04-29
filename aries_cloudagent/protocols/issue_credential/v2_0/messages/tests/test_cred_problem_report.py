from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CRED_20_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..cred_problem_report import V20CredProblemReport


class TestCredProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = V20CredProblemReport()
        assert prob._type == DIDCommPrefix.qualify_current(CRED_20_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V20CredProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = V20CredProblemReport()

        prob = V20CredProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.cred_problem_report."
        "V20CredProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = V20CredProblemReport()

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = V20CredProblemReport()
        data = prob.serialize()
        model_instance = V20CredProblemReport.deserialize(data)
        assert isinstance(model_instance, V20CredProblemReport)
