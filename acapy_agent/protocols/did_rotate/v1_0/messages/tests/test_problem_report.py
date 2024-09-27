from unittest import TestCase, mock

from ......protocols.didcomm_prefix import DIDCommPrefix
from ...message_types import PROBLEM_REPORT, PROTOCOL_PACKAGE
from ...messages.problem_report import RotateProblemReport


class TestRotateProblemReport(TestCase):
    def test_init_type(self):
        """Test initializer."""

        obj = RotateProblemReport()
        assert obj._type == DIDCommPrefix.qualify_current(PROBLEM_REPORT)

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.problem_report.RotateProblemReportSchema.load"
    )
    def test_deserialize(self, mock_rotate_ack_schema_load):
        """Test deserialization."""

        obj = RotateProblemReport()
        rotate_ack = RotateProblemReport.deserialize(obj)
        mock_rotate_ack_schema_load.assert_called_once_with(obj)
        assert rotate_ack is mock_rotate_ack_schema_load.return_value

    @mock.patch(
        f"{PROTOCOL_PACKAGE}.messages.problem_report.RotateProblemReportSchema.dump"
    )
    def test_serialize(self, mock_rotate_ack_schema_dump):
        """Test serialization."""

        obj = RotateProblemReport()
        rotate_ack_dict = obj.serialize()
        mock_rotate_ack_schema_dump.assert_called_once_with(obj)
        assert rotate_ack_dict is mock_rotate_ack_schema_dump.return_value

    def test_serde(self):
        obj = {
            "~thread": {"thid": "test-thid", "pthid": "test-pthid"},
            "problem_items": [{"did": "test-did", "reason": "test-reason"}],
        }
        rotate_ack = RotateProblemReport.deserialize(obj)
        assert rotate_ack._type == DIDCommPrefix.qualify_current(PROBLEM_REPORT)

        rotate_ack_dict = rotate_ack.serialize()
        assert rotate_ack_dict["problem_items"] == obj["problem_items"]

    def test_make_model(self):
        """Test making model."""

        obj = RotateProblemReport(
            problem_items=[{"did": "test-did", "reason": "test-reason"}]
        )
        obj.assign_thread_id("test-thid", "test-pthid")
        rotate_ack_dict = obj.serialize()
        rotate_ack = RotateProblemReport.deserialize(rotate_ack_dict)
        assert isinstance(rotate_ack, RotateProblemReport)
