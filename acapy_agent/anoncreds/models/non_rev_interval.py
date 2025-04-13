"""AnonCreds non-revocation interval."""

from time import time
from typing import Optional

from marshmallow import EXCLUDE, fields

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import INT_EPOCH_EXAMPLE, INT_EPOCH_VALIDATE


class AnonCredsNonRevocationInterval(BaseModel):
    """AnonCreds non-revocation interval."""

    class Meta:
        """NonRevocationInterval metadata."""

        schema_class = "AnonCredsNonRevocationIntervalSchema"

    def __init__(self, fro: Optional[int] = None, to: Optional[int] = None, **kwargs):
        """Initialize non-revocation interval.

        Args:
            fro: earliest time of interest
            to: latest time of interest
            kwargs: additional attributes

        """
        super().__init__(**kwargs)
        self.fro = fro
        self.to = to

    def covers(self, timestamp: Optional[int] = None) -> bool:
        """Whether input timestamp (default now) lies within non-revocation interval.

        Args:
            timestamp: time of interest

        Returns:
            whether input time satisfies non-revocation interval

        """
        timestamp = timestamp or int(time())
        return (self.fro or 0) <= timestamp <= (self.to or timestamp)

    def timestamp(self) -> bool:
        """Return a timestamp that the non-revocation interval covers."""
        return self.to or self.fro or int(time())


class AnonCredsNonRevocationIntervalSchema(BaseModelSchema):
    """Schema to allow serialization/deserialization of non-revocation intervals."""

    class Meta:
        """AnonCredsNonRevocationIntervalSchema metadata."""

        model_class = AnonCredsNonRevocationInterval
        unknown = EXCLUDE

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
