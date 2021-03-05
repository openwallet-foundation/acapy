"""Issue-credential protocol message attachment format."""

from collections import namedtuple
from re import sub
from typing import Mapping, Sequence, Type, Union
from enum import Enum
from uuid import uuid4

from marshmallow import EXCLUDE, fields, validate

from .....utils.classloader import ClassLoader
from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import UUIDFour
from .....messaging.decorators.attach_decorator import AttachDecorator
from ..message_types import PROTOCOL_PACKAGE
from ..models.detail.indy import V20CredExRecordIndy
from ..models.detail.ld_proof import V20CredExRecordLDProof
from typing import TYPE_CHECKING

# TODO: remove
if TYPE_CHECKING:
    from ..formats.handler import V20CredFormatHandler

FormatSpec = namedtuple("FormatSpec", "aries aka detail handler")


class V20CredFormat(BaseModel):
    """Issue-credential protocol message attachment format."""

    class Meta:
        """Issue-credential protocol message attachment format metadata."""

        schema_class = "V20CredFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy-zkp-v1.0",
            ["indy", "hyperledgerindy", "hlindy"],
            V20CredExRecordIndy,
            f"{PROTOCOL_PACKAGE}.formats.indy.IndyCredFormatHandler",
        )
        LD_PROOF = FormatSpec(
            "dif/credential-manifest@v1.0",
            ["ldproof", "jsonld"],
            V20CredExRecordLDProof,
            f"{PROTOCOL_PACKAGE}.formats.ld_proof.LDProofCredFormatHandler",
        )

        @classmethod
        def get(cls, label: Union[str, "V20CredFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V20CredFormat.Format:
                    if (
                        fmt.aries == label
                        or sub("[^a-zA-Z0-9]+", "", label.lower()) in fmt.aka
                    ):
                        return fmt
            elif isinstance(label, V20CredFormat.Format):
                return label

            return None

        @property
        def aries(self) -> str:
            """Accessor for aries identifier."""
            return self.value.aries

        @property
        def aka(self) -> str:
            """Accessor for alternative identifier list."""
            return self.value.aka

        @property
        def api(self) -> str:
            """Admin API specifier."""
            return self.name.lower()

        @property
        def detail(self) -> str:
            """Accessor for credential exchange detail class."""
            return self.value.detail

        @property
        def handler(self) -> Type["V20CredFormatHandler"]:
            """Accessor for credential exchange format handler."""
            # TODO: optimize / refactor
            return ClassLoader.load_class(self.value.handler)

        def validate_filter(self, data: Mapping):
            """Raise ValidationError for wrong filtration criteria."""
            self.handler.validate_filter(data)

        def get_attachment_data(
            self,
            formats: Sequence["V20CredFormat"],
            attachments: Sequence[AttachDecorator],
        ):
            """Find attachment of current format, base64-decode and return its data."""
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
        format_: Union[str, "V20CredFormat.Format"] = None,
    ):
        """Initialize issue-credential protocol message attachment format."""
        self.attach_id = attach_id or uuid4()
        self.format_ = (
            V20CredFormat.Format.get(format_) or V20CredFormat.Format.INDY
        ).aries

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
        description="Attachment identifier",
        example=UUIDFour.EXAMPLE,
    )
    format_ = fields.Str(
        required=True,
        allow_none=False,
        description="Acceptable issue-credential message attachment format specifier",
        data_key="format",
        validate=validate.OneOf([f.aries for f in V20CredFormat.Format]),
        example=V20CredFormat.Format.INDY.aries,
    )
