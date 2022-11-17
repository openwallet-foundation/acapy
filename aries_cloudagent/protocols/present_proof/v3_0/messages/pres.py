"""A (proof) presentation content message."""

from marshmallow import EXCLUDE, fields, validates_schema, ValidationError
from typing import Sequence

from .....messaging.agent_message import (
    AgentMessage,
    AgentMessageSchemaV2,
)
from .....messaging.decorators.attach_decorator_didcomm_v2_pres import (
    AttachDecorator,
    AttachDecoratorSchema,
)

from ..message_types import PRES_30, PROTOCOL_PACKAGE

from .pres_format import V30PresFormat
from .pres_body import V30PresBody, V30PresBodySchema


HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.pres_handler.V30PresHandler"


class V30Pres(AgentMessage):
    """Class representing a presentation."""

    class Meta:
        """Presentation metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "V30PresSchema"
        message_type = PRES_30

    def __init__(
        self,
        _id: str = None,
        *,
        body: V30PresBody = None,
        attachments: Sequence[AttachDecorator] = None,
        **kwargs,
    ):
        """
        Initialize presentation object.

        Args:
            attachments: attachments
            comment: optional comment

        """
        super().__init__(_id=_id, **kwargs)
        self.body = body
        # self.formats = formats if formats else []
        self.attachments = list(attachments) if attachments else []

    def attachment(self, fmt: V30PresFormat.Format = None) -> dict:
        """Return attachment if exists else returns none."""

        if len(self.attachments) != 0:
            for att in self.attachments:
                try:
                    if V30PresFormat.Format.get(att.format.format).api == fmt.api:
                        return att.content
                except AttributeError:
                    return None
        else:
            return None


class V30PresSchema(AgentMessageSchemaV2):
    """Presentation schema."""

    class Meta:
        """Presentation schema metadata."""

        model_class = V30Pres
        unknown = EXCLUDE

    body = fields.Nested(
        # presentation-msg has no field will_confirm
        V30PresBodySchema(only=("comment", "goal_code")),
        comment="Human-readable comment",
        description="Body descriptor with GoalCode made for PresProof",
        data_key="body",  # def name of field just to make sure
        example="hier könnt ihr body-example stehen",
        required=True,
        allow_none=False,
    )

    attachments = fields.Nested(
        # AttachDecoratorSchema, required=True, many=True, data_key="presentations~attach"
        # Put V30PresFormatSchema inside AttachDecorator
        AttachDecoratorSchema,
        many=True,
        required=False,
        data_key="attachments",
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate presentation attachment per format."""
        print(f"data {data}")
        attachments = data.get("attachments") or []
        print(f"attach{attachments}")
        formats = []
        for atch in attachments:
            formats.append(atch.format)
        print(f"formats {formats}")

        if len(formats) != len(attachments):
            raise ValidationError("Formats/attachments length mismatch")

        for atch in attachments:
            # atch = get_attach_by_id(fmt.attach_id)
            pres_format = V30PresFormat.Format.get(atch.format.format)
            if pres_format:
                pres_format.validate_fields(PRES_30, atch.content)
