"""Credential format inner object."""

from enum import Enum
from typing import Mapping, Sequence, Union
from uuid import uuid4

from marshmallow import EXCLUDE, fields, validate, ValidationError

from ......messaging.credential_definitions.util import CRED_DEF_TAGS
from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.valid import UUIDFour


class V20CredFormat(BaseModel):
    """Credential format."""

    class Meta:
        """Credential format metadata."""

        schema_class = "V20CredFormatSchema"

    class Format(Enum):
        """Proposal credential format."""

        INDY = "hlindy-zkp-v1.0"
        DIF = "dif/credential-manifest@v1.0"  # placeholder for W3C

        @classmethod
        def get(cls, label: Union[str, "V20CredFormat.Format"]):
            """Get format enum for label."""
            if isinstance(label, str):
                for fmt in V20CredFormat.Format:
                    if fmt.value == label:
                        return fmt
            elif isinstance(label, V20CredFormat.Format):
                return label
            return None

        def validate_filter(self, data: Mapping):
            """Raise ValidationError for wrong filtration criteria."""
            if self is V20CredFormat.Format.INDY:
                if data.keys() - set(CRED_DEF_TAGS):
                    raise ValidationError(f"Bad indy credential filter: {data}")

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
                    return atch.indy_dict

            return None

    def __init__(
        self,
        *,
        attach_id: str = None,
        format_: Union[str, "V20CredFormat.Format"] = None,
    ):
        """Initialize cred format."""
        self.attach_id = attach_id or uuid4()
        self.format_ = (
            V20CredFormat.Format.get(format_) or V20CredFormat.Format.INDY
        ).value

    @property
    def format(self):
        """Return format."""
        return self.format_


class V20CredFormatSchema(BaseModelSchema):
    """Credential format schema."""

    class Meta:
        """Credential format schema metadata."""

        model_class = V20CredFormat
        unknown = EXCLUDE

    attach_id = fields.Str(
        required=True,
        allow_none=False,
        description="attachment identifier",
        example=UUIDFour.EXAMPLE,
    )
    format_ = fields.Str(
        required=True,
        allow_none=False,
        description="acceptable credential format specifier",
        data_key="format",
        validate=validate.OneOf([f.value for f in V20CredFormat.Format]),
        example=V20CredFormat.Format.INDY.value,
    )
