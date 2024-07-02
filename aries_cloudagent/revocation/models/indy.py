"""Indy utilities for revocation."""

from time import time

from marshmallow import fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import INT_EPOCH_EXAMPLE, INT_EPOCH_VALIDATE


class NonRevocationInterval(BaseModel):
    """Indy non-revocation interval."""

    class Meta:
        """NonRevocationInterval metadata."""

        schema_class = "NonRevocationIntervalSchema"

    def __init__(self, timestamp_from: int = None, timestamp_to: int = None, **kwargs):
        """Initialize non-revocation interval.

        Args:
            timestamp_from: earliest time of interest
            timestamp_to: latest time of interest
            kwargs: additional keyword arguments

        """
        super().__init__(**kwargs)
        self.timestamp_from = timestamp_from
        self.timestamp_to = timestamp_to

    def covers(self, timestamp: int = None) -> bool:
        """Whether input timestamp (default now) lies within non-revocation interval.

        Args:
            timestamp: time of interest

        Returns:
            whether input time satisfies non-revocation interval

        """
        timestamp = timestamp or int(time())
        return (
            (self.timestamp_from or 0) <= timestamp <= (self.timestamp_to or timestamp)
        )

    def timestamp(self) -> bool:
        """Return a timestamp that the non-revocation interval covers."""
        return self.timestamp_to or self.timestamp_from or int(time())


class NonRevocationIntervalSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of non-revocation intervals."""

    class Meta:
        """NonRevocationIntervalSchema metadata."""

        model_class = NonRevocationInterval

    fro = fields.Int(
        required=False,
        data_key="from",
        validate=INT_EPOCH_VALIDATE,
        metadata={
            "description": "Earliest time of interest in non-revocation interval",
            "strict": True,
            "example": INT_EPOCH_EXAMPLE,
        },
    )
    to = fields.Int(
        required=False,
        validate=INT_EPOCH_VALIDATE,
        metadata={
            "description": "Latest time of interest in non-revocation interval",
            "strict": True,
            "example": INT_EPOCH_EXAMPLE,
        },
    )
