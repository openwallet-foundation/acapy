"""Key pair record."""

from typing import Any

from marshmallow import fields, EXCLUDE

from ...messaging.models.base_record import (
    BaseRecord,
    BaseRecordSchema,
)
from ...messaging.valid import UUIDFour
from ...wallet.crypto import KeyType


class KeyPairRecord(BaseRecord):
    """Represents a key pair record."""

    class Meta:
        """KeyPairRecord metadata."""

        schema_class = "KeyPairRecordSchema"

    RECORD_TYPE = "key_pair_record"
    RECORD_ID_NAME = "key_id"

    TAG_NAMES = {"public_key_b58", "key_type"}

    def __init__(
        self,
        *,
        key_id: str = None,
        public_key_b58: str = None,
        private_key_b58: str = None,
        key_type: str = None,
        **kwargs,
    ):
        """Initialize a new KeyPairRecord."""
        super().__init__(key_id, **kwargs)
        self.public_key_b58 = public_key_b58
        self.private_key_b58 = private_key_b58
        self.key_type = key_type

    @property
    def key_id(self) -> str:
        """Accessor for the ID associated with this record."""
        return self._id

    @property
    def record_value(self) -> dict:
        """Accessor for the JSON record value generated for this record."""
        return {
            prop: getattr(self, prop)
            for prop in ("public_key_b58", "private_key_b58", "key_type")
        }

    def __eq__(self, other: Any) -> bool:
        """Comparison between records."""
        return super().__eq__(other)


class KeyPairRecordSchema(BaseRecordSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """KeyPairRecordSchema metadata."""

        model_class = KeyPairRecord
        unknown = EXCLUDE

    key_id = fields.Str(
        required=True,
        description="Wallet key ID",
        example=UUIDFour.EXAMPLE,
    )
    public_key_b58 = fields.Str(
        required=True,
        description="Base 58 encoded public key",
        example=(
            "o1cocewfMSeasDPVYEkbmeEZUan5fM7ix2oWxeZupgVQFqXRsxUFdAjDmxoosqgdn"
            "QJruhMYE3q7gx65MMdgtj67UsUJgJsFYX5ruMyZ58pttzKxnJrM2aoAbhqL1rnQWFf"
        ),
    )
    private_key_b58 = fields.Str(
        required=True,
        description="Base 58 encoded private key",
        example="4xPeQ2sVw8S9opkARzeL6SSgygGiq6JQjFViwXL8v2wE",
    )
    key_type = fields.Str(
        required=True, description="Type of key", example=KeyType.BLS12381G2.key_type
    )
