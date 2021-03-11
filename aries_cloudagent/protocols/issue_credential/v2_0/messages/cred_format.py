"""Issue-credential protocol message attachment format."""

from collections import namedtuple
from enum import Enum
from re import sub
from typing import Mapping, Sequence, Union
from uuid import uuid4

from marshmallow import EXCLUDE, fields, validate, ValidationError

from .....messaging.credential_definitions.util import CRED_DEF_TAGS
from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import UUIDFour

from ...indy.cred import IndyCredentialSchema
from ...indy.cred_abstract import IndyCredAbstractSchema
from ...indy.cred_request import IndyCredRequestSchema

from ..models.detail.dif import V20CredExRecordDIF
from ..models.detail.indy import V20CredExRecordIndy

# Aries RFC value, further monikers, cred ex detail record class
FormatSpec = namedtuple("FormatSpec", "aries aka detail")


class V20CredFormat(BaseModel):
    """Issue-credential protocol message attachment format."""

    class Meta:
        """Issue-credential protocol message attachment format metadata."""

        schema_class = "V20CredFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy@v2.0",
            {"indy", "hyperledgerindy", "hlindy"},
            V20CredExRecordIndy,
        )
        DIF = FormatSpec(
            "dif@v1.0",
            {"dif", "w3c", "jsonld"},
            V20CredExRecordDIF,
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

        def validate_filter_attach(self, data: Mapping):
            """Raise ValidationError for wrong filtration criteria."""
            if self is V20CredFormat.Format.INDY:
                if data.keys() - set(CRED_DEF_TAGS):
                    raise ValidationError(f"Bad indy credential filter: {data}")

        def validate_offer_attach(self, data: Mapping):
            """Raise ValidationError for wrong offer attachment format."""
            if self is V20CredFormat.Format.INDY:
                IndyCredAbstractSchema().load(data)

        def validate_request_attach(self, data: Mapping):
            """Raise ValidationError for wrong request attachment format."""
            if self is V20CredFormat.Format.INDY:
                IndyCredRequestSchema().load(data)

        def validate_credential_attach(self, data: Mapping):
            """Raise ValidationError for wrong credential attachment format."""
            if self is V20CredFormat.Format.INDY:
                IndyCredentialSchema().load(data)

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
