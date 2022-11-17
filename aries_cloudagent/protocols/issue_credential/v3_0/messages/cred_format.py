"""Issue-credential protocol message attachment format."""

from collections import namedtuple
from enum import Enum
from typing import Mapping, Type, TYPE_CHECKING, Union


from marshmallow import EXCLUDE, fields

from .....utils.classloader import DeferLoad

from .....messaging.models.base import BaseModel, BaseModelSchema

from ..models.detail.indy import V30CredExRecordIndy
from ..models.detail.ld_proof import V30CredExRecordLDProof

if TYPE_CHECKING:
    from ..formats.handler import V30CredFormatHandler

FormatSpec = namedtuple("FormatSpec", "aries detail handler")


class V30CredFormat(BaseModel):
    """Issue-credential protocol message attachment format."""

    class Meta:
        """Issue-credential protocol message attachment format metadata."""

        schema_class = "V30CredFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy/",
            V30CredExRecordIndy,
            DeferLoad(
                "aries_cloudagent.protocols.issue_credential.v3_0"
                ".formats.indy.handler.IndyCredFormatHandler"
            ),
        )
        LD_PROOF = FormatSpec(
            "aries/",
            V30CredExRecordLDProof,
            DeferLoad(
                "aries_cloudagent.protocols.issue_credential.v3_0"
                ".formats.ld_proof.handler.LDProofCredFormatHandler"
            ),
        )

        @classmethod
        def get(cls, label: Union[str, "V30CredFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V30CredFormat.Format:
                    if label.startswith(fmt.aries) or label == fmt.api:
                        return fmt
            elif isinstance(label, V30CredFormat.Format):
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
        def detail(self) -> Union[V30CredExRecordIndy, V30CredExRecordLDProof]:
            """Accessor for credential exchange detail class."""
            return self.value.detail

        @property
        def handler(self) -> Type["V30CredFormatHandler"]:
            """Accessor for credential exchange format handler."""
            return self.value.handler.resolved

        def validate_fields(self, message_type: str, attachment_data: Mapping):
            """Raise ValidationError for invalid attachment formats."""
            self.handler.validate_fields(message_type, attachment_data)

    def __init__(self, *, format_: str = None, **kwargs):
        """Initialize issue-credential protocol message attachment format."""
        self.format_ = format_

    @property
    def format(self) -> str:
        """Return format."""
        return self.format_


class V30CredFormatSchema(BaseModelSchema):
    """Issue-credential protocol message attachment format schema."""

    class Meta:
        """Issue-credential protocol message attachment format schema metadata."""

        model_class = V30CredFormat
        unknown = EXCLUDE

    format_ = fields.Str(
        required=False,
        allow_none=False,
        description="Attachment format specifier",
        data_key="format",
        example="aries/ld-proof-vc-detail@v1.0",
    )
