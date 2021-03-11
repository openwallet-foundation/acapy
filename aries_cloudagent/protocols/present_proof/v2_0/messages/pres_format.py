"""Credential format inner object."""

from collections import namedtuple
from enum import Enum
from re import sub
from typing import Mapping, Sequence, Union
from uuid import uuid4

from marshmallow import EXCLUDE, fields, validate

from .....messaging.decorators.attach_decorator import AttachDecorator
from .....messaging.models.base import BaseModel, BaseModelSchema
from .....messaging.valid import UUIDFour

from ...indy.proof import IndyProofSchema
from ...indy.proof_request import IndyProofRequestSchema

FormatSpec = namedtuple("FormatSpec", "aries aka")  # Aries RFC value, further monikers


class V20PresFormat(BaseModel):
    """Present-proof protocol message attachment format."""

    class Meta:
        """Present-proof protocol message attachment format metadata."""

        schema_class = "V20PresFormatSchema"

    class Format(Enum):
        """Attachment format."""

        INDY = FormatSpec(
            "hlindy@v2.0",
            {"indy", "hyperledgerindy", "hlindy"},
        )
        DIF = FormatSpec(
            "dif@v1.0",
            {"dif", "w3c", "jsonld"},
        )

        @classmethod
        def get(cls, label: Union[str, "V20PresFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V20PresFormat.Format:
                    if (
                        fmt.aries == label
                        or sub("[^a-zA-Z0-9]+", "", label.lower()) in fmt.aka
                    ):
                        return fmt
            elif isinstance(label, V20PresFormat.Format):
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

        def validate_request_attach(self, data: Mapping):
            """Raise ValidationError for wrong proposal/request content."""
            if self is V20PresFormat.Format.INDY:
                IndyProofRequestSchema().load(data)

        def validate_pres_attach(self, data: Mapping):
            """Raise ValidationError for wrong presentation content."""
            if self is V20PresFormat.Format.INDY:
                IndyProofSchema().load(data)

        def get_attachment_data(
            self,
            formats: Sequence["V20PresFormat"],
            attachments: Sequence[AttachDecorator],
        ):
            """Find attachment of current format, base64-decode and return its data."""
            for fmt in formats:
                if V20PresFormat.Format.get(fmt.format) is self:
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
        format_: Union[str, "V20PresFormat.Format"] = None,
    ):
        """Initialize present-proof protocol message attachment format."""
        self.attach_id = attach_id or uuid4()
        self.format_ = (
            V20PresFormat.Format.get(format_) or V20PresFormat.Format.INDY
        ).aries

    @property
    def format(self) -> str:
        """Return format."""
        return self.format_


class V20PresFormatSchema(BaseModelSchema):
    """Present-proof protocol message attachment format schema."""

    class Meta:
        """Present-proof protocol message attachment format schema metadata."""

        model_class = V20PresFormat
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
        description="Acceptable present-proof message attachment format specifier",
        data_key="format",
        validate=validate.OneOf([f.aries for f in V20PresFormat.Format]),
        example=V20PresFormat.Format.INDY.aries,
    )
