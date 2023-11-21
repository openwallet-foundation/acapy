import pytest

from unittest import mock

from ......messaging.models.base import BaseModelError
from .....didcomm_prefix import DIDCommPrefix
from ...message_types import PROBLEM_REPORT
from ..problem_report import DIDXProblemReport

from .. import problem_report as test_module

THID = "dummy-thid"
PTHID = "dummy-pthid"


def test_init_type():
    complete = DIDXProblemReport()
    assert complete._type == DIDCommPrefix.qualify_current(PROBLEM_REPORT)


def test_serde():
    obj = {
        "~thread": {"thid": THID, "pthid": PTHID},
        "description": {"code": "complete_not_accepted", "en": "test"},
    }
    report = DIDXProblemReport.deserialize(obj)
    assert report._type == DIDCommPrefix.qualify_current(PROBLEM_REPORT)
    complete_dict = report.serialize()
    assert complete_dict["~thread"] == obj["~thread"]


def test_missing_code():
    with pytest.raises(BaseModelError):
        DIDXProblemReport.deserialize({"description": {"en": "test"}})


def test_unrecognized_code():
    with mock.patch.object(test_module, "LOGGER", autospec=True) as mock_logger:
        DIDXProblemReport.deserialize(
            {"description": {"code": "unknown", "en": "test"}}
        )
    mock_logger.warning.assert_called_once()
