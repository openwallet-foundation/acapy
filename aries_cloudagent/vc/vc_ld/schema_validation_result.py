"""Presentation schema validation result classes."""

from typing import List, Optional

from marshmallow import fields

from ...messaging.models.base import BaseModel, BaseModelSchema

class ValidationResult(BaseModel):
    """Presentation validation result class."""

    class Meta:
        """ValidationResult metadata."""

        schema_class = "ValidationResultSchema"

    def __init__(
        self,
        *,
        validated: bool,
        errors: Optional[List[Exception]] = None,
    ) -> None:
        """Create new ValidationResult instance."""
        self.validated = validated
        self.errors = errors

    def __repr__(self) -> str:
        """Return a human readable representation of this class.

        Returns:
            A human readable string for this class

        """
        items = ("{}={}".format(k, repr(v)) for k, v in self.__dict__.items())
        return "<{}({})>".format(self.__class__.__name__, ", ".join(items))

    def __eq__(self, other: object) -> bool:
        """Comparison between presentation validation results."""
        if isinstance(other, ValidationResult):
            return (
                self.validated == other.validated
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


class ValidationResultSchema(BaseModelSchema):
    """Presentation validation result schema."""

    class Meta:
        """ValidationResultSchema metadata."""

        model_class = ValidationResult

    validated = fields.Bool(required=True)
    errors = fields.List(fields.Field())
