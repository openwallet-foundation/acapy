"""Test Problem Report Message."""

import pytest

from unittest import mock
from unittest import TestCase

from ......messaging.models.base import BaseModelError

from ..problem_report import (
    CMProblemReport,
    CMProblemReportSchema,
    ProblemReportReason,
    ValidationError,
)

from .. import problem_report as test_module


class TestCMProblemReportMessage(TestCase):
    """Test problem report."""

    def test_make_model(self):
        """Make problem report model."""
        data = CMProblemReport(
            description={
                "en": "Insufficient credit",
                "code": ProblemReportReason.MEDIATION_NOT_GRANTED.value,
            }
        ).serialize()
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
        with mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger:
            CMProblemReportSchema().validate_fields(data)
        mock_logger.warning.assert_called_once()
