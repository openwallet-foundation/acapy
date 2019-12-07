from unittest import mock, TestCase

from .....messaging.models.base import BaseModelError
from ...message_types import PROBLEM_REPORT
from ..problem_report import ProblemReport, ProblemReportReason


class TestProblemReportSchema(TestCase):

    problem_report = ProblemReport(
        problem_code=ProblemReportReason.RESPONSE_PROCESSING_ERROR.value,
        explain="Response processing error",
    )

    def test_make_model(self):
        data = self.problem_report.serialize()
        model_instance = ProblemReport.deserialize(data)
        assert isinstance(model_instance, ProblemReport)
