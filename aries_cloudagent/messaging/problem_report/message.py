"""Represents a generic problem report message."""

from typing import Mapping, Sequence

from marshmallow import fields

from ..agent_message import AgentMessage, AgentMessageSchema

HANDLER_CLASS = "aries_cloudagent.messaging.problem_report.handler.ProblemReportHandler"

MESSAGE_TYPE = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/notification/1.0/problem-report"


class ProblemReport(AgentMessage):
    """Base class representing a generic problem report message."""

    class Meta:
        """Problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = MESSAGE_TYPE
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
        **kwargs
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

    msg_catalog = fields.Str(data_key="@msg_catalog", required=False)
    locale = fields.Str(data_key="@locale", required=False)
    explain_ltxt = fields.Str(data_key="explain-ltxt", required=False)
    explain_l10n = fields.Dict(fields.Str(), fields.Str(), required=False)
    problem_items = fields.List(
        fields.Dict(fields.Str(), fields.Str()),
        data_key="problem-items",
        required=False,
    )
    who_retries = fields.Str(data_key="who-retries", required=False)
    fix_hint_ltxt = fields.Dict(
        fields.Str(), fields.Str(), data_key="fix-hint-ltxt", required=False
    )
    impact = fields.Str(required=False)
    where = fields.Str(required=False)
    time_noticed = fields.Str(data_key="time-noticed", required=False)
    tracking_uri = fields.Str(data_key="tracking-uri", required=False)
    escalation_uri = fields.Str(data_key="escalation-uri", required=False)
