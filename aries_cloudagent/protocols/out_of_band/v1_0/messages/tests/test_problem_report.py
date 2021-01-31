import pytest
from unittest import mock, TestCase
from asynctest import TestCase as AsyncTestCase
from ......messaging.models.base import BaseModelError
from ..problem_report import ProblemReport, ProblemReportReason


class TestProblemReportMessage(TestCase):
    """Test request schema."""

    problem_report = ProblemReport(
        problem_code=ProblemReportReason.EXISTING_CONNECTION_NOT_ACTIVE.value,
        explain="Test",
    )

    def test_init(self):
        """Test initialization of Handshake Reuse message."""
        self.problem_report.assign_thread_id(thid="test_thid", pthid="test_pthid")
        assert isinstance(self.problem_report, ProblemReport)
        assert isinstance(self.problem_report._id, str)
        assert len(self.problem_report._id) > 4
        assert self.problem_report._thread.thid == "test_thid"
        assert self.problem_report._thread.pthid == "test_pthid"

    def test_make_model(self):
        self.problem_report.assign_thread_id(thid="test_thid", pthid="test_pthid")
        data = self.problem_report.serialize()
        model_instance = ProblemReport.deserialize(data)
        assert isinstance(model_instance, ProblemReport)
