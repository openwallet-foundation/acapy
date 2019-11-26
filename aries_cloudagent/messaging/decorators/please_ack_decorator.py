"""The please-ack decorator (~please_ack) to request acknowledgement."""

from typing import Sequence

from marshmallow import fields

from ..models.base import BaseModel, BaseModelSchema
from ..valid import UUIDFour


class PleaseAckDecorator(BaseModel):
    """Class representing the please-ack decorator."""

    class Meta:
        """PleaseAckDecorator metadata."""

        schema_class = "PleaseAckDecoratorSchema"

    def __init__(
        self,
        message_id: str = None,
        on: Sequence[str] = None,
    ):
        """
        Initialize a PleaseAckDecorator instance.

        Args:
            message_id: identifier of message to acknowledge, if not current message
            on: list of tokens describing circumstances for acknowledgement.

        """
        super().__init__()
        self.message_id = message_id
        self.on = list(on) if on else None

    def __eq__(self, other):
        """Equality comparator."""

        return (
            type(self) == type(other) and
            self.message_id == other.message_id and
            (set(self.on or []) == set(other.on or []))
        )


class PleaseAckDecoratorSchema(BaseModelSchema):
    """PleaseAck decorator schema used in serialization/deserialization."""

    class Meta:
        """PleaseAckDecoratorSchema metadata."""

        model_class = PleaseAckDecorator

    message_id = fields.Str(
       description="Message identifier",
       example=UUIDFour.EXAMPLE,
       required=False,
       allow_none=False,
    )
    on = fields.List(
        fields.Str(example="OUTCOME"),
        description="List of tokens describing circumstances for acknowledgement",
        required=False,
    )
