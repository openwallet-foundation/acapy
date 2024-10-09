"""Proof verification and validation result classes."""

from typing import Any, List, Optional

from marshmallow import fields

from ...messaging.models.base import BaseModel, BaseModelSchema


class PurposeResult(BaseModel):
    """Proof purpose result class."""

    class Meta:
        """PurposeResult metadata."""

        schema_class = "PurposeResultSchema"

    def __init__(
        self,
        *,
        valid: bool,
        error: Optional[str] = None,
        controller: Optional[Any] = None,
    ) -> None:
        """Create new PurposeResult instance."""
        self.valid = valid
        self.error = error
        self.controller = controller

    def __repr__(self) -> str:
        """Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between proof purpose results."""
        if isinstance(other, PurposeResult):
            return (
                self.valid == other.valid
                and self.error == other.error
                and self.controller == other.controller
            )
        return False


class PurposeResultSchema(BaseModelSchema):
    """Proof purpose result schema."""

    class Meta:
        """PurposeResultSchema metadata."""

        model_class = PurposeResult

    valid = fields.Boolean()
    error = fields.Str()
    controller = fields.Dict()


class ProofResult(BaseModel):
    """Proof result class."""

    class Meta:
        """ProofResult metadata."""

        schema_class = "ProofResultSchema"

    def __init__(
        self,
        *,
        verified: bool,
        proof: Optional[dict] = None,
        error: Optional[str] = None,
        purpose_result: Optional[PurposeResult] = None,
    ) -> None:
        """Create new ProofResult instance."""
        self.verified = verified
        self.proof = proof
        self.error = error
        self.purpose_result = purpose_result

    def __repr__(self) -> str:
        """Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between proof results."""
        if isinstance(other, ProofResult):
            return (
                self.verified == other.verified
                and self.proof == other.proof
                and self.error == other.error
                and self.purpose_result == other.purpose_result
            )
        return False


class ProofResultSchema(BaseModelSchema):
    """Proof result schema."""

    class Meta:
        """ProofResultSchema metadata."""

        model_class = ProofResult

    verified = fields.Boolean()
    proof = fields.Dict()
    error = fields.Str()
    purpose_result = fields.Nested(PurposeResultSchema)


class DocumentVerificationResult(BaseModel):
    """Domain verification result class."""

    class Meta:
        """DocumentVerificationResult metadata."""

        schema_class = "DocumentVerificationResultSchema"

    def __init__(
        self,
        *,
        verified: bool,
        document: Optional[dict] = None,
        results: Optional[List[ProofResult]] = None,
        errors: Optional[List[str]] = None,
    ) -> None:
        """Create new DocumentVerificationResult instance."""
        self.verified = verified
        self.document = document
        self.results = results
        self.errors = errors

    def __repr__(self) -> str:
        """Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between document verification results."""
        if isinstance(other, DocumentVerificationResult):
            return (
                self.verified == other.verified
                and self.document == other.document
                # check results list
                and (
                    # both not present
                    (not self.results and not other.results)
                    # both list and matching
                    or (
                        isinstance(self.results, list)
                        and isinstance(other.results, list)
                        and all(
                            self_result == other_result
                            for (self_result, other_result) in zip(
                                self.results, other.results
                            )
                        )
                    )
                )
                # check error list
                and (
                    # both not present
                    (not self.errors and not other.errors)
                    # both list and matching
                    or (
                        isinstance(self.errors, list)
                        and isinstance(other.errors, list)
                        and all(
                            self_error == other_error
                            for (self_error, other_error) in zip(
                                self.errors, other.errors
                            )
                        )
                    )
                )
            )
        return False


class DocumentVerificationResultSchema(BaseModelSchema):
    """Document verification result schema."""

    class Meta:
        """DocumentVerificationResultSchema metadata."""

        model_class = DocumentVerificationResult

    verified = fields.Boolean(required=True)
    document = fields.Dict(required=False)
    results = fields.Nested(ProofResultSchema, many=True)
    errors = fields.List(fields.Str(), required=False)
