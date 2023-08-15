"""Revocation artifacts."""

from typing import Sequence

from marshmallow import EXCLUDE, fields, validate

from ...messaging.models.base import BaseModel, BaseModelSchema
from ...messaging.valid import (
    BASE58_SHA256_HASH_EXAMPLE,
    BASE58_SHA256_HASH_VALIDATE,
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_REV_REG_ID_VALIDATE,
    INDY_VERSION_EXAMPLE,
    INDY_VERSION_VALIDATE,
    NATURAL_NUM_EXAMPLE,
    NATURAL_NUM_VALIDATE,
)


class IndyRevRegDefValuePublicKeysAccumKey(BaseModel):
    """Indy revocation registry definition value public keys accum key."""

    class Meta:
        """Indy revocation registry definition value public keys accum key metadata."""

        schema_class = "IndyRevRegDefValuePublicKeysAccumKeySchema"

    def __init__(self, z: str = None):
        """Initialize."""

        self.z = z


class IndyRevRegDefValuePublicKeysAccumKeySchema(BaseModelSchema):
    """Indy revocation registry definition value public keys accum key schema."""

    class Meta:
        """Schema metadata."""

        model_class = IndyRevRegDefValuePublicKeysAccumKey
        unknown = EXCLUDE

    z = fields.Str(
        metadata={
            "description": "Value for z",
            "example": "1 120F522F81E6B7 1 09F7A59005C4939854",
        }
    )


class IndyRevRegDefValuePublicKeys(BaseModel):
    """Indy revocation registry definition value public keys."""

    class Meta:
        """Model metadata."""

        schema_class = "IndyRevRegDefValuePublicKeysSchema"

    def __init__(self, accum_key: IndyRevRegDefValuePublicKeysAccumKey = None):
        """Initialize."""

        self.accum_key = accum_key


class IndyRevRegDefValuePublicKeysSchema(BaseModelSchema):
    """Indy revocation registry definition value public keys schema."""

    class Meta:
        """Schema metadata."""

        model_class = IndyRevRegDefValuePublicKeys
        unknown = EXCLUDE

    accum_key = fields.Nested(
        IndyRevRegDefValuePublicKeysAccumKeySchema(), data_key="accumKey"
    )


class IndyRevRegDefValue(BaseModel):
    """Indy revocation registry definition value."""

    class Meta:
        """Model metadata."""

        schema_class = "IndyRevRegDefValueSchema"

    def __init__(
        self,
        issuance_type: str = None,
        max_cred_num: int = None,
        public_keys: IndyRevRegDefValuePublicKeys = None,
        tails_hash: str = None,
        tails_location: str = None,
    ):
        """Initialize."""
        self.issuance_type = issuance_type
        self.max_cred_num = max_cred_num
        self.public_keys = public_keys
        self.tails_hash = tails_hash
        self.tails_location = tails_location


class IndyRevRegDefValueSchema(BaseModelSchema):
    """Indy revocation registry definition value schema."""

    class Meta:
        """Schema metadata."""

        model_class = IndyRevRegDefValue
        unknown = EXCLUDE

    issuance_type = fields.Str(
        validate=validate.OneOf(["ISSUANCE_ON_DEMAND", "ISSUANCE_BY_DEFAULT"]),
        data_key="issuanceType",
        metadata={"description": "Issuance type"},
    )
    max_cred_num = fields.Int(
        data_key="maxCredNum",
        validate=NATURAL_NUM_VALIDATE,
        metadata={
            "description": "Maximum number of credentials; registry size",
            "strict": True,
            "example": NATURAL_NUM_EXAMPLE,
        },
    )
    public_keys = fields.Nested(
        IndyRevRegDefValuePublicKeysSchema(),
        data_key="publicKeys",
        metadata={"description": "Public keys"},
    )
    tails_hash = fields.Str(
        data_key="tailsHash",
        validate=BASE58_SHA256_HASH_VALIDATE,
        metadata={
            "description": "Tails hash value",
            "example": BASE58_SHA256_HASH_EXAMPLE,
        },
    )
    tails_location = fields.Str(
        data_key="tailsLocation", metadata={"description": "Tails file location"}
    )


class IndyRevRegDef(BaseModel):
    """Indy revocation registry definition."""

    class Meta:
        """Model metadata."""

        schema_class = "IndyRevRegDefSchema"

    def __init__(
        self,
        ver: str = None,
        id_: str = None,
        revoc_def_type: str = None,
        tag: str = None,
        cred_def_id: str = None,
        value: IndyRevRegDefValue = None,
    ):
        """Initialize."""

        self.ver = ver
        self.id_ = id_
        self.revoc_def_type = revoc_def_type
        self.tag = tag
        self.cred_def_id = cred_def_id
        self.value = value


class IndyRevRegDefSchema(BaseModelSchema):
    """Indy revocation registry definition schema."""

    class Meta:
        """Schema metadata."""

        model_class = IndyRevRegDef
        unknown = EXCLUDE

    ver = fields.Str(
        validate=INDY_VERSION_VALIDATE,
        metadata={
            "description": "Version of revocation registry definition",
            "example": INDY_VERSION_EXAMPLE,
        },
    )
    id_ = fields.Str(
        data_key="id",
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Indy revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    revoc_def_type = fields.Str(
        data_key="revocDefType",
        validate=validate.Equal("CL_ACCUM"),
        metadata={
            "description": "Revocation registry type (specify CL_ACCUM)",
            "example": "CL_ACCUM",
        },
    )
    tag = fields.Str(metadata={"description": "Revocation registry tag"})
    cred_def_id = fields.Str(
        data_key="credDefId",
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    value = fields.Nested(
        IndyRevRegDefValueSchema(),
        metadata={"description": "Revocation registry definition value"},
    )


class IndyRevRegEntryValue(BaseModel):
    """Indy revocation registry entry value."""

    class Meta:
        """Model metadata."""

        schema_class = "IndyRevRegEntryValueSchema"

    def __init__(
        self,
        prev_accum: str = None,
        accum: str = None,
        revoked: Sequence[int] = None,
    ):
        """Initialize."""
        self.prev_accum = prev_accum
        self.accum = accum
        self.revoked = revoked


class IndyRevRegEntryValueSchema(BaseModelSchema):
    """Indy revocation registry entry value schema."""

    class Meta:
        """Schema metadata."""

        model_class = "IndyRevRegEntryValue"
        unknown = EXCLUDE

    prev_accum = fields.Str(
        data_key="prevAccum",
        required=False,
        metadata={
            "description": "Previous accumulator value",
            "example": "21 137AC810975E4 6 76F0384B6F23",
        },
    )
    accum = fields.Str(
        metadata={
            "description": "Accumulator value",
            "example": "21 11792B036AED0AAA12A4 4 298B2571FFC63A737",
        }
    )
    revoked = fields.List(
        fields.Int(metadata={"strict": True}),
        required=False,
        metadata={"description": "Revoked credential revocation identifiers"},
    )


class IndyRevRegEntry(BaseModel):
    """Indy revocation registry entry."""

    class Meta:
        """Model metadata."""

        schema_class = "IndyRevRegEntrySchema"

    def __init__(self, ver: str = None, value: IndyRevRegEntryValue = None):
        """Initialize."""

        self.ver = ver
        self.value = value


class IndyRevRegEntrySchema(BaseModelSchema):
    """Indy revocation registry entry schema."""

    class Meta:
        """Schema metadata."""

        model_class = IndyRevRegEntry
        unknown = EXCLUDE

    ver = fields.Str(
        validate=INDY_VERSION_VALIDATE,
        metadata={
            "description": "Version of revocation registry entry",
            "example": INDY_VERSION_EXAMPLE,
        },
    )
    value = fields.Nested(
        IndyRevRegEntryValueSchema(),
        metadata={"description": "Revocation registry entry value"},
    )
