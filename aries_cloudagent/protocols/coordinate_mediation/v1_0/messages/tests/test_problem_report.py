"""Test Problem Report Message."""
import logging
import pytest

from unittest import mock, TestCase

from ......messaging.models.base import BaseModelError

from ..problem_report import (
    CMProblemReport,
    CMProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)


class TestCMProblemReportMessage(TestCase):
    """Test problem report."""

    def setUp(self):
        self.problem_report = CMProblemReport(
            description={
                "en": "Insufficient credit",
                "code": ProblemReportReason.MEDIATION_NOT_GRANTED.value,
            }
        )

    @pytest.fixture(autouse=True)
    def inject_fixtures(self, caplog):
        self._caplog = caplog

    def test_make_model(self):
        """Make problem report model."""
        data = self.problem_report.serialize()
        model_instance = CMProblemReport.deserialize(data)
        assert isinstance(model_instance, CMProblemReport)

        model_instance.description["code"] = "extraneous code"
        with pytest.raises(BaseModelError):
            CMProblemReport.deserialize(model_instance)

    def test_validate_x(self):
        """Exercise validation requirements."""
        schema = CMProblemReportSchema()
        with pytest.raises(ValidationError):
            schema.validate_fields({})

    def test_validate_and_logger(self):
        """Capture ValidationError and Logs."""
        data = CMProblemReport(
            description={
                "en": "Insufficient credit",
                "code": "invalid_code",
            },
        ).serialize()
        self._caplog.set_level(logging.WARNING)
        CMProblemReportSchema().validate_fields(data)
        assert "Unexpected error code received" in self._caplog.text
