"""Issue-credential protocol message attachment format."""

from collections import namedtuple
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Sequence, Type, Union
from uuid import uuid4

from marshmallow import EXCLUDE, fields

from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import UUID4_EXAMPLE
from .....utils.classloader import DeferLoad
from ..models.detail.indy import V20CredExRecordIndy
from ..models.detail.ld_proof import V20CredExRecordLDProof

if TYPE_CHECKING:
    from ..formats.handler import V20CredFormatHandler

FormatSpec = namedtuple("FormatSpec", "aries detail handler")


class V20CredFormat(BaseModel):
    """Issue-credential protocol message attachment format."""

    class Meta:
        """Issue-credential protocol message attachment format metadata."""

        schema_class = "V20CredFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy/",
            V20CredExRecordIndy,
            DeferLoad(
                "aries_cloudagent.protocols.issue_credential.v2_0"
                ".formats.indy.handler.IndyCredFormatHandler"
            ),
        )
        LD_PROOF = FormatSpec(
            "aries/",
            V20CredExRecordLDProof,
            DeferLoad(
                "aries_cloudagent.protocols.issue_credential.v2_0"
                ".formats.ld_proof.handler.LDProofCredFormatHandler"
            ),
        )

        @classmethod
        def get(cls, label: Union[str, "V20CredFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V20CredFormat.Format:
                    if label.startswith(fmt.aries) or label == fmt.api:
                        return fmt
            elif isinstance(label, V20CredFormat.Format):
                return label

            return None

        @property
        def api(self) -> str:
            """Admin API specifier."""
            return self.name.lower()

        @property
        def aries(self) -> str:
            """Aries specifier prefix."""
            return self.value.aries

        @property
        def detail(self) -> Union[V20CredExRecordIndy, V20CredExRecordLDProof]:
            """Accessor for credential exchange detail class."""
            return self.value.detail

        @property
        def handler(self) -> Type["V20CredFormatHandler"]:
            """Accessor for credential exchange format handler."""
            return self.value.handler.resolved

        def validate_fields(self, message_type: str, attachment_data: Mapping):
            """Raise ValidationError for invalid attachment formats."""
            self.handler.validate_fields(message_type, attachment_data)

        def get_attachment_data(
            self,
            formats: Sequence["V20CredFormat"],
            attachments: Sequence[AttachDecorator],
        ):
            """Find attachment of current format, decode and return its content."""
            for fmt in formats:
                if V20CredFormat.Format.get(fmt.format) is self:
                    attach_id = fmt.attach_id
                    break
            else:
                return None

            for atch in attachments:
                if atch.ident == attach_id:
                    return atch.content

            return None

    def __init__(
        self,
        *,
        attach_id: str = None,
        format_: str = None,
    ):
        """Initialize issue-credential protocol message attachment format."""
        self.attach_id = attach_id or uuid4()
        self.format_ = format_

    @property
    def format(self) -> str:
        """Return format."""
        return self.format_


class V20CredFormatSchema(BaseModelSchema):
    """Issue-credential protocol message attachment format schema."""

    class Meta:
        """Issue-credential protocol message attachment format schema metadata."""

        model_class = V20CredFormat
        unknown = EXCLUDE

    attach_id = fields.Str(
        required=True,
        allow_none=False,
        metadata={"description": "Attachment identifier", "example": UUID4_EXAMPLE},
    )
    format_ = fields.Str(
        required=True,
        allow_none=False,
        data_key="format",
        metadata={
            "description": "Attachment format specifier",
            "example": "aries/ld-proof-vc-detail@v1.0",
        },
    )
