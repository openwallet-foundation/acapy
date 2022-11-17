"""Credential body inner object."""
from collections import namedtuple
from marshmallow import EXCLUDE, fields
from typing import Union
from .....messaging.models.base import BaseModel, BaseModelSchema


# aries prefix
FormatSpec = namedtuple("FormatSpec", "aries handler")
BodySpec = namedtuple("BodySpec", "aries handler")  # what does this do??


class V30PresBody(BaseModel):
    """Present-proof protocol message attachment for body field."""

    class Meta:
        """Present-proof protocol message attachment body metadata."""

        schema_class = "V30PresBodySchema"

    # prev in pres_format: def of INDY and DIF cred format

    def __init__(
        self, *, goal_code: str = None, comment: str = None, will_confirm: bool = False
    ):
        """Initialize present-proof protocol message attachment format."""
        self.goal_code = goal_code
        self.comment = comment
        # as it was used in pres_request Schema to init the field
        self.will_confirm = will_confirm or False

    @classmethod
    def get(self, cls, label: Union[str, "V30PresBody.Body"]):
        """Get Body enum for label."""
        # TODO to return meaningful Exception
        return self.goal_code


class V30PresBodySchema(BaseModelSchema):
    """Present-proof protocol message attachment Body schema."""

    class Meta:
        """Present-proof protocol message attachment body schema metadata."""

        model_class = V30PresBody
        unknown = EXCLUDE

    goal_code = fields.Str(
        required=False,
        description="optional field that indicates the goal of the message sender.",
        example="hier könnte ihr goal code example stehen",
        allow_none=True,
    )
    comment = fields.Str(
        required=False,
        description="Human readably comment",
        example="hier könnte ihr Comment example stehen",
    )

    # only used in request-presentation msg
    # not in presentation msg, propose presentation
    will_confirm = fields.Bool(
        required=False,
        descritption="will_confirm : an optional field that defaults to false, to indicate\
             that the verifier will or will not send a post-presentation \
                confirmation ack message",
        example="hier könnte ihr Will_Confirm example stehen: True/False,",
        allow_none=True,
    )
