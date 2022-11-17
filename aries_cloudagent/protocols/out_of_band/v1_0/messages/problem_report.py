"""Represents an OOB connection reuse problem report message."""

import logging

from enum import Enum
from typing import Optional, Text

from marshmallow import (
    EXCLUDE,
    fields,
    pre_dump,
    validates_schema,
    ValidationError,
)

from ....problem_report.v1_0.message import ProblemReport, ProblemReportSchema

from ..message_types import PROBLEM_REPORT, PROTOCOL_PACKAGE, DEFAULT_VERSION

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers"
    ".problem_report_handler.OOBProblemReportMessageHandler"
)

LOGGER = logging.getLogger(__name__)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    NO_EXISTING_CONNECTION = "no_existing_connection"
    EXISTING_CONNECTION_NOT_ACTIVE = "existing_connection_not_active"


class OOBProblemReport(ProblemReport):
    """Base class representing an OOB connection reuse problem report message."""

    class Meta:
        """OOB connection reuse problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "OOBProblemReportSchema"

    def __init__(
        self,
        version: str = DEFAULT_VERSION,
        msg_type: Optional[Text] = None,
        *args,
        **kwargs,
    ):
        """Initialize a ProblemReport message instance."""
        super().__init__(_type=msg_type, _version=version, *args, **kwargs)


class OOBProblemReportSchema(ProblemReportSchema):
    """Schema for ProblemReport base class."""

    class Meta:
        """Metadata for problem report schema."""

        model_class = OOBProblemReport
        unknown = EXCLUDE

    _type = fields.Str(
        data_key="@type",
        required=False,
        description="Message type",
        example="https://didcomm.org/my-family/1.0/my-message-type",
    )

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid and pthid, are mandatory."""

        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid", "pthid"}:
            raise ValidationError("Missing required field(s) in thread decorator")

        return obj

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields."""

        if not data.get("description", {}).get("code", ""):
            raise ValidationError("Value for description.code must be present")
        elif data.get("description", {}).get("code", "") not in [
            prr.value for prr in ProblemReportReason
        ]:
            locales = list(data.get("description").keys())
            locales.remove("code")
            LOGGER.warning(
                "Unexpected error code received.\n"
                f"Code: {data.get('description').get('code')}, "
                f"Description: {data.get('description').get(locales[0])}"
            )
