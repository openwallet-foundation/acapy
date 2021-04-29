from unittest import mock, TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CREDENTIAL_PROBLEM_REPORT, PROTOCOL_PACKAGE

from ..credential_problem_report import CredentialProblemReport


class TestCredentialProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = CredentialProblemReport()
        assert prob._type == DIDCommPrefix.qualify_current(CREDENTIAL_PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "CredentialProblemReportSchema.load"
    )
    def test_deserialize(self, mock_load):
        """Test deserialization."""

        obj = CredentialProblemReport()

        prob = CredentialProblemReport.deserialize(obj)
        mock_load.assert_called_once_with(obj)

        assert prob is mock_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.credential_problem_report."
        "CredentialProblemReportSchema.dump"
    )
    def test_serialize(self, mock_dump):
        """Test serialization."""

        obj = CredentialProblemReport()

        ser = obj.serialize()
        mock_dump.assert_called_once_with(obj)

        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = CredentialProblemReport()
        data = prob.serialize()
        model_instance = CredentialProblemReport.deserialize(data)
        assert isinstance(model_instance, CredentialProblemReport)
