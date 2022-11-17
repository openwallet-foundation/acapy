"""Represents a generic problem report message."""

from typing import Mapping, Sequence

from marshmallow import EXCLUDE, fields, validate, validates_schema, ValidationError

from ....messaging.agent_message import AgentMessage, AgentMessageSchema
from ....messaging.valid import RFC3339_DATETIME

from .message_types import PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handler.ProblemReportHandler"


class ProblemReport(AgentMessage):
    """Base class representing a generic problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "ProblemReportSchema"

    def __init__(
        self,
        *,
        description: Mapping[str, str] = None,
        problem_items: Sequence[Mapping[str, str]] = None,
        who_retries: str = None,
        fix_hint: Mapping[str, str] = None,
        impact: str = None,
        where: str = None,
        noticed_time: str = None,
        tracking_uri: str = None,
        escalation_uri: str = None,
        **kwargs,
    ):
        """
        Initialize a ProblemReport message instance.

        Args:
            description: Human-readable, localized string(s) explaining the problem
            problem_items: List of problem items
            who_retries: you | me | both | none
            fix_hint: Dictionary of localized hints
            impact: message | thread | connection
            where: you | me | other (cloud | edge | wire | agency ..)
            noticed_time: Datetime when the problem was noticed
            tracking_uri: URI for tracking the problem
            escalation_uri: URI for escalating the problem
        """
        super().__init__(**kwargs)
        self.description = description if description else None
        self.problem_items = problem_items if problem_items else None
        self.who_retries = who_retries
        self.fix_hint = dict(fix_hint) if fix_hint else None
        self.impact = impact
        self.where = where
        self.noticed_time = noticed_time
        self.tracking_uri = tracking_uri
        self.escalation_uri = escalation_uri


class ProblemReportSchema(AgentMessageSchema):
    """Schema for ProblemReport base class."""

    class Meta:
        """Problem report schema metadata."""

        model_class = ProblemReport
        unknown = EXCLUDE

    description = fields.Dict(
        keys=fields.Str(description="Locale or 'code'", example="en-US"),
        values=fields.Str(description="Problem description or error code"),
        required=False,
        description="Human-readable localized problem descriptions",
    )
    problem_items = fields.List(
        fields.Dict(
            keys=fields.Str(description="Problematic parameter or item"),
            values=fields.Str(description="Problem text/number/value"),
            description="Problem item",
        ),
        data_key="problem-items",
        required=False,
        description="List of problem items",
    )
    who_retries = fields.Str(
        data_key="who-retries",
        required=False,
        description="Party to retry: you, me, both, none",
        example="you",
        validate=validate.OneOf(["you", "me", "both", "none"]),
    )
    fix_hint = fields.Dict(
        keys=fields.Str(description="Locale", example="en-US"),
        values=fields.Str(
            description="Localized message", example="Synchronize time to NTP"
        ),
        required=False,
        description="Human-readable localized suggestions how to fix problem",
    )
    impact = fields.Str(
        required=False,
        description="Breadth of impact of problem: message, thread, or connection",
        example="thread",
        validate=validate.OneOf(["message", "thread", "connection"]),
    )
    where = fields.Str(
        required=False,
        description="Where the error occurred, from reporter perspective",
        example="you - agency",
        validate=validate.Regexp(r"(you)|(me)|(other) - .+"),
    )
    time_noticed = fields.Str(
        data_key="time-noticed",
        required=False,
        description="Problem detection time, precision at least day up to millisecond",
        **RFC3339_DATETIME,
    )
    tracking_uri = fields.Str(
        required=False,
        description="URI allowing recipient to track error status",
        example="http://myservice.com/status",
    )
    escalation_uri = fields.Str(
        required=False,
        description="URI to supply additional help",
        example="mailto://help.desk@myservice.com",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has neither indy nor ld_proof

        """
        if not data.get("description", {}).get("code"):
            raise ValidationError("Field description.code must have a value")
