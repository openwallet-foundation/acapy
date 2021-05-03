import pytest

from unittest import mock, TestCase

from .....messaging.models.base import BaseModelError

from ....didcomm_prefix import DIDCommPrefix

from ..message_types import PROBLEM_REPORT
from ..message import ProblemReport, ProblemReportSchema


class TestProblemReport(TestCase):
    """Problem report tests."""

    def test_init_type(self):
        """Test initializer."""

        prob = ProblemReport(
            description={
                "en": "oh no",
                "code": "abandoned",
            }
        )
        assert prob._type == DIDCommPrefix.qualify_current(PROBLEM_REPORT)

    def test_deserialize(self):
        """Test deserialization."""

        obj = ProblemReport(
            description={
                "en": "oh no",
                "code": "abandoned",
            }
        )

        with mock.patch.object(
            ProblemReportSchema, "load", mock.MagicMock()
        ) as mock_load:
            prob = ProblemReport.deserialize(obj)

        mock_load.assert_called_once_with(obj)
        assert prob is mock_load.return_value

    def test_serialize(self):
        """Test serialization."""

        obj = ProblemReport(
            description={
                "en": "oh no",
                "code": "abandoned",
            }
        )

        with mock.patch.object(
            ProblemReportSchema, "dump", mock.MagicMock()
        ) as mock_dump:
            ser = obj.serialize()

        mock_dump.assert_called_once_with(obj)
        assert ser is mock_dump.return_value

    def test_make_model(self):
        """Test making model."""

        prob = ProblemReport(
            description={
                "en": "oh no",
                "code": "abandoned",
            }
        )
        data = prob.serialize()
        model_instance = ProblemReport.deserialize(data)
        assert isinstance(model_instance, ProblemReport)

        prob = ProblemReport()
        data = prob.serialize()
        with pytest.raises(BaseModelError):
            ProblemReport.deserialize(data)
