"""Credential format inner object."""

from collections import namedtuple
from enum import Enum
from marshmallow import EXCLUDE, fields
from typing import Mapping, Type, Union, TYPE_CHECKING

from .....messaging.models.base import BaseModel, BaseModelSchema
from .....utils.classloader import DeferLoad

if TYPE_CHECKING:
    from ..formats.handler import V30PresFormatHandler

# aries prefix
FormatSpec = namedtuple("FormatSpec", "aries handler")


class V30PresFormat(BaseModel):
    """Present-proof protocol message attachment format."""

    class Meta:
        """Present-proof protocol message attachment format metadata."""

        schema_class = "V30PresFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy/",
            DeferLoad(
                "aries_cloudagent.protocols.present_proof.v3_0"
                ".formats.indy.handler.IndyPresExchangeHandler"
            ),
        )
        DIF = FormatSpec(
            "dif/",
            DeferLoad(
                "aries_cloudagent.protocols.present_proof.v3_0"
                ".formats.dif.handler.DIFPresFormatHandler"
            ),
        )

        @classmethod
        def get(cls, label: Union[str, "V30PresFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V30PresFormat.Format:
                    if label.startswith(fmt.aries) or label == fmt.api:
                        return fmt
            elif isinstance(label, V30PresFormat.Format):
                return label

            return None

        @property
        def api(self) -> str:
            """Admin API specifier."""
            return self.name.lower()

        @property
        def aries(self) -> str:
            """Accessor for aries identifier."""
            return self.value.aries

        @property
        def handler(self) -> Type["V30PresFormatHandler"]:
            """Accessor for presentation exchange format handler."""
            return self.value.handler.resolved

        def validate_fields(self, message_type: str, attachment_data: Mapping):
            """Raise ValidationError for invalid attachment formats."""
            self.handler.validate_fields(message_type, attachment_data)

    def __init__(self, *, format_: str = None, **kwargs):
        """Initialize present-proof protocol message attachment format."""
        self.format_ = format_

    @property
    def format(self) -> str:
        """Return format."""
        return self.format_


class V30PresFormatSchema(BaseModelSchema):
    """Present-proof protocol message attachment format schema."""

    class Meta:
        """Present-proof protocol message attachment format schema metadata."""

        model_class = V30PresFormat
        unknown = EXCLUDE

    format_ = fields.Str(
        required=False,
        allow_none=False,
        description="Attachment format specifier",
        data_key="format",
        example="dif/presentation-exchange/submission@v1.0",
    )
