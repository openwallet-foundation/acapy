from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CREDENTIAL_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..credential_problem_report import IssueCredentialV10ProblemReport


class TestCredentialProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = IssueCredentialV10ProblemReport()
        assert prob._type == DIDCommPrefix.qualify_current(CREDENTIAL_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "IssueCredentialV10ProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = IssueCredentialV10ProblemReport()

        prob = IssueCredentialV10ProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "IssueCredentialV10ProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = IssueCredentialV10ProblemReport()

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = IssueCredentialV10ProblemReport()
        data = prob.serialize()
        model_instance = IssueCredentialV10ProblemReport.deserialize(data)
        assert isinstance(model_instance, IssueCredentialV10ProblemReport)
