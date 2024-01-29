"""Test Problem Report Message."""

import pytest

from unittest import mock
from unittest import TestCase

from ......messaging.models.base import BaseModelError

from ..problem_report import (
    OOBProblemReport,
    OOBProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)

from .. import problem_report as test_module


class TestOOBProblemReportMessage(TestCase):
    """Test problem report."""

    def setUp(self):
        self.problem_report = OOBProblemReport(
            description={
                "en": "Test",
                "code": ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
            }
        )

    def test_init(self):
        """Test initialization."""
        self.problem_report.assign_thread_id(thid="test_thid", pthid="test_pthid")
        assert isinstance(self.problem_report, OOBProblemReport)
        assert isinstance(self.problem_report._id, str)
        assert len(self.problem_report._id) > 4
        assert self.problem_report._thread.thid == "test_thid"
        assert self.problem_report._thread.pthid == "test_pthid"

    def test_make_model(self):
        """Make problem report model."""
        self.problem_report.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = self.problem_report.serialize()
        model_instance = OOBProblemReport.deserialize(data)
        assert isinstance(model_instance, OOBProblemReport)

        model_instance.description["code"] = "extraneous code"
        with pytest.raises(BaseModelError):
            OOBProblemReport.deserialize(model_instance)

    def test_pre_dump_x(self):
        """Exercise pre-dump serialization requirements."""
        with pytest.raises(BaseModelError):
            data = self.problem_report.serialize()

    def test_validate_x(self):
        """Exercise validation requirements."""
        schema = OOBProblemReportSchema()
        with pytest.raises(ValidationError):
            schema.validate_fields({})

    def test_validate_and_logger(self):
        """Capture ValidationError and Logs."""
        data = OOBProblemReport(
            description={
                "en": "Insufficient credit",
                "code": "invalid_code",
            },
        )
        data.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = data.serialize()
        with mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger:
            OOBProblemReportSchema().validate_fields(data)
        assert mock_logger.warning.call_count == 1

    def test_assign_msg_type_version_to_model_inst(self):
        test_msg = OOBProblemReport()
        assert "1.1" in test_msg._type
        assert "1.1" in OOBProblemReport.Meta.message_type
        test_msg = OOBProblemReport(version="1.2")
        assert "1.2" in test_msg._type
        assert "1.1" in OOBProblemReport.Meta.message_type
