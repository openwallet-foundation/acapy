"""Represents a generic problem report message."""

from typing import Mapping, Sequence

from marshmallow import fields, validate

from ...messaging.agent_message import AgentMessage, AgentMessageSchema

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
        msg_catalog: str = None,
        locale: str = None,
        explain_ltxt: str = None,
        explain_l10n: Mapping[str, str] = None,
        problem_items: Sequence[Mapping[str, str]] = None,
        who_retries: str = None,
        fix_hint_ltxt: Mapping[str, str] = None,
        impact: str = None,
        where: str = None,
        time_noticed: str = None,
        tracking_uri: str = None,
        escalation_uri: str = None,
        **kwargs,
    ):
        """
        Initialize a ProblemReport message instance.

        Args:
            msg_catalog: Reference to a message catalog
            locale: Locale identifier
            explain_ltxt: Localized message
            explain_l10n: Dictionary of localizations
            problem_items: List of problem items
            who_retries: you | me | both | none
            fix_hint_ltxt: Dictionary of localized hints
            impact: message | thread | connection
            where: you | me | other (cloud | edge | wire | agency ..)
            time_noticed: Datetime when the problem was noticed
            tracking_uri: URI for tracking the problem
            escalation_uri: URI for escalating the problem
        """
        super(ProblemReport, self).__init__(**kwargs)
        self.msg_catalog = msg_catalog
        self.locale = locale
        self.explain_ltxt = explain_ltxt
        self.explain_l10n = explain_l10n
        self.problem_items = problem_items
        self.who_retries = who_retries
        self.fix_hint_ltxt = fix_hint_ltxt
        self.impact = impact
        self.where = where
        self.time_noticed = time_noticed
        self.tracking_uri = tracking_uri
        self.escalation_uri = escalation_uri


class ProblemReportSchema(AgentMessageSchema):
    """Schema for ProblemReport base class."""

    class Meta:
        """Problem report schema metadata."""

        model_class = ProblemReport

    msg_catalog = fields.Str(
        data_key="@msg_catalog",
        required=False,
        description="Reference to a message catalog",
        example="did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/error-codes",
    )
    locale = fields.Str(
        data_key="@locale", required=False, description="Locale", example="en-US",
    )
    explain_ltxt = fields.Str(
        data_key="explain-ltxt",
        required=False,
        description="Localized message",
        example="Item not found",
    )
    explain_l10n = fields.Dict(
        keys=fields.Str(description="Locale"),
        values=fields.Str(description="Localized message"),
        required=False,
        description="Dictionary of localizations",
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
    fix_hint_ltxt = fields.Dict(
        keys=fields.Str(description="Locale", example="en-US"),
        values=fields.Str(
            description="Localized message", example="Synchronize time to NTP"
        ),
        data_key="fix-hint-ltxt",
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
        example="1970-01-01 00:00:00.000Z",
        validate=validate.Regexp(
            r"^\d{4}-\d\d-\d\d"
            r"(?:(?: \d\d:\d\d(?:\:\d\d(?:\.\d{1,6})?)(?:[+=]\d\d:?\d\d|Z)?)?)$"
        ),
    )
    tracking_uri = fields.Str(
        data_key="tracking-uri",
        required=False,
        description="URI allowing recipient to track error status",
        example="http://myservice.com/status",
    )
    escalation_uri = fields.Str(
        data_key="escalation-uri",
        required=False,
        description="URI to supply additional help",
        example="mailto://help.desk@myservice.com",
    )
