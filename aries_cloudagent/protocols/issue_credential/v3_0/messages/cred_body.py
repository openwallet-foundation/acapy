"""Credential body inner object."""

from .inner.cred_preview import V30CredPreview, V30CredPreviewSchema
from collections import namedtuple
from marshmallow import EXCLUDE, fields
from .....messaging.models.base import BaseModel, BaseModelSchema

FormatSpec = namedtuple("FormatSpec", "aries handler")
BodySpec = namedtuple("BodySpec", "aries handler")


class V30CredBody(BaseModel):
    """Issue credential protocol message attachment for body field."""

    class Meta:
        """Issue credentialf protocol message attachment body metadata."""

        schema_class = "V30CredBodySchema"

    def __init__(
        self,
        *,
        goal_code: str = None,
        comment: str = None,
        replacement_id: str = None,
        credential_preview: V30CredPreview = None
    ):
        """Initialize present-proof protocol message attachment format."""
        self.goal_code = goal_code
        self.comment = comment
        self.replacement_id = replacement_id
        self.credential_preview = credential_preview

    def __iter__(self):
        """Iterate through V30CredBody."""
        for attr, value in self.__dict__.items():
            yield attr, value


class V30CredBodySchema(BaseModelSchema):
    """Present-proof protocol message attachment Body schema."""

    class Meta:
        """Present-proof protocol message attachment body schema metadata."""

        model_class = V30CredBody
        unknown = EXCLUDE

    goal_code = fields.Str(
        required=False,
        description="optional field that indicates the goal of the message sender.",
        example="hier könnte ihr goal code example stehen",
        data_key="goal_code",
        allow_none=True,
    )
    comment = fields.Str(
        required=False,
        description="Human readably comment",
        example="hier könnte ihr Comment example stehen",
        data_key="comment",
        allow_none=True,
    )

    replacement_id = fields.Str(
        required=False,
        description="optinal field to coordinal credential replacement",
        example="unique id",
        data_key="replacement_id",
        allow_none=True,
    )

    credential_preview = fields.Nested(
        V30CredPreviewSchema, required=False, allow_none=False
    )
