"""Represents a rotate problem report message."""

from enum import Enum

from marshmallow import EXCLUDE, ValidationError, pre_dump, validates_schema

from .....protocols.problem_report.v1_0.message import (
    ProblemReport,
    ProblemReportSchema,
)
from ..message_types import PROBLEM_REPORT, PROTOCOL_PACKAGE

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.problem_report_handler.ProblemReportHandler"
)


class ProblemReportReason(Enum):
    """Supported reason codes."""

    UNRESOLVABLE = "e.did.unresolvable"
    METHOD_UNSUPPORTED = "e.did.method_unsupported"


class RotateProblemReport(ProblemReport):
    """Base class representing a Rotate problem report message."""

    class Meta:
        """Rotate problem report metadata."""

        handler_class = HANDLER_CLASS
        message_type = PROBLEM_REPORT
        schema_class = "RotateProblemReportSchema"

    @classmethod
    def for_code(cls, problem_code: ProblemReportReason, did: str, **kwargs):
        """Initialize a ProblemReport message instance for a specific problem code.

        Args:
            problem_code: The standard error identifier
            did: The DID contained in the rotate message the problem report is about
            kwargs: Optional keyword arguments to pass through to the problem report
                constructor
        Returns:
            An instance of RotateProblemReport
        """
        description = {
            ProblemReportReason.UNRESOLVABLE: "DID Unresolvable",
            ProblemReportReason.METHOD_UNSUPPORTED: "DID Method Unsupported",
        }[problem_code]
        return cls(
            description={
                "en": description,
                "code": problem_code.value,
            },
            problem_items=[
                {"did": did},
            ],
            **kwargs,
        )

    @classmethod
    def unresolvable(cls, did: str, **kwargs):
        """Initialize a ProblemReport message instance for an unresolvable DID.

        Args:
            did: The DID contained in the rotate message the problem report is about
            kwargs: Optional keyword arguments to pass through to the problem report
                constructor
        Returns:
            An instance of RotateProblemReport
        """
        return cls.for_code(ProblemReportReason.UNRESOLVABLE, did, **kwargs)

    @classmethod
    def method_unsupported(cls, did: str, **kwargs):
        """Initialize a ProblemReport message instance for an unsupported DID method.

        Args:
            did: The DID contained in the rotate message the problem report is about
            kwargs: Optional keyword arguments to pass through to the problem report
                constructor
        Returns:
            An instance of RotateProblemReport
        """
        return cls.for_code(ProblemReportReason.METHOD_UNSUPPORTED, did, **kwargs)


class RotateProblemReportSchema(ProblemReportSchema):
    """Schema for RotateProblemReport base class."""

    class Meta:
        """Metadata for Rotate problem report schema."""

        model_class = RotateProblemReport
        unknown = EXCLUDE

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data is invalid

        """
        if "problem_items" not in data or not data["problem_items"]:
            raise ValidationError("Rotate problem report must contain problem_items")

        if "did" not in data["problem_items"][0]:
            raise ValidationError(
                "Rotate problem report problem_items must contain did"
            )

    @pre_dump
    def check_thread_deco(self, obj, **kwargs):
        """Thread decorator, and its thid, are mandatory."""
        if not obj._decorators.to_dict().get("~thread", {}).keys() >= {"thid"}:
            raise ValidationError("Missing required field(s) in thread decorator")
        return obj
