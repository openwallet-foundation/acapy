"""The please-ack decorator to request acknowledgement."""

from typing import Sequence

from marshmallow import EXCLUDE, fields

from ..models.base import BaseModel, BaseModelSchema


class PleaseAckDecorator(BaseModel):
    """Class representing the please-ack decorator."""

    class Meta:
        """PleaseAckDecorator metadata."""

        schema_class = "PleaseAckDecoratorSchema"

    def __init__(
        self,
        on: Sequence[str]
    ):
        """Initialize a PleaseAckDecorator instance.

        Args:
            message_id: identifier of message to acknowledge, if not current message
            on: list of tokens describing circumstances for acknowledgement.

        """
        super().__init__()
        self.on = list(on)


class PleaseAckDecoratorSchema(BaseModelSchema):
    """PleaseAck decorator schema used in serialization/deserialization."""

    class Meta:
        """PleaseAckDecoratorSchema metadata."""

        model_class = PleaseAckDecorator
        unknown = EXCLUDE

    on = fields.List(
        fields.Str(metadata={"example": "OUTCOME"}),
        required=True,
        metadata={
            "description": "List of tokens describing circumstances for acknowledgement"
        },
    )
