"""Schema artifacts."""

from marshmallow import Schema, fields

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_VERSION_EXAMPLE,
    INDY_VERSION_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
)


class CredDefValuePrimarySchema(OpenAPISchema):
    """Cred def value primary schema."""

    n = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    s = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    r = fields.Nested(
        Schema.from_dict(
            {
                "master_secret": fields.Str(
                    validate=NUM_STR_WHOLE_VALIDATE,
                    metadata={"example": NUM_STR_WHOLE_EXAMPLE},
                ),
                "number": fields.Str(
                    validate=NUM_STR_WHOLE_VALIDATE,
                    metadata={"example": NUM_STR_WHOLE_EXAMPLE},
                ),
                "remainder": fields.Str(
                    validate=NUM_STR_WHOLE_VALIDATE,
                    metadata={"example": NUM_STR_WHOLE_EXAMPLE},
                ),
            }
        ),
        metadata={"name": "CredDefValuePrimaryRSchema"},
    )
    rctxt = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )
    z = fields.Str(
        validate=NUM_STR_WHOLE_VALIDATE, metadata={"example": NUM_STR_WHOLE_EXAMPLE}
    )


class CredDefValueRevocationSchema(OpenAPISchema):
    """Cred def value revocation schema."""

    g = fields.Str(metadata={"example": "1 1F14F&ECB578F 2 095E45DDF417D"})
    g_dash = fields.Str(
        metadata={"example": "1 1D64716fCDC00C 1 0C781960FA66E3D3 2 095E45DDF417D"}
    )
    h = fields.Str(metadata={"example": "1 16675DAE54BFAE8 2 095E45DD417D"})
    h0 = fields.Str(metadata={"example": "1 21E5EF9476EAF18 2 095E45DDF417D"})
    h1 = fields.Str(metadata={"example": "1 236D1D99236090 2 095E45DDF417D"})
    h2 = fields.Str(metadata={"example": "1 1C3AE8D1F1E277 2 095E45DDF417D"})
    htilde = fields.Str(metadata={"example": "1 1D8549E8C0F8 2 095E45DDF417D"})
    h_cap = fields.Str(
        metadata={"example": "1 1B2A32CF3167 1 2490FEBF6EE55 1 0000000000000000"}
    )
    u = fields.Str(
        metadata={"example": "1 0C430AAB2B4710 1 1CB3A0932EE7E 1 0000000000000000"}
    )
    pk = fields.Str(
        metadata={"example": "1 142CD5E5A7DC 1 153885BD903312 2 095E45DDF417D"}
    )
    y = fields.Str(
        metadata={"example": "1 153558BD903312 2 095E45DDF417D 1 0000000000000000"}
    )


class CredDefValueSchema(OpenAPISchema):
    """Cred def value schema."""

    primary = fields.Nested(
        CredDefValuePrimarySchema(),
        metadata={"description": "Primary value for credential definition"},
    )
    revocation = fields.Nested(
        CredDefValueRevocationSchema(),
        metadata={"description": "Revocation value for credential definition"},
    )


class CredentialDefinitionSchema(OpenAPISchema):
    """Marshmallow schema for indy cred def."""

    ver = fields.Str(
        validate=INDY_VERSION_VALIDATE,
        metadata={
            "description": "Node protocol version",
            "example": INDY_VERSION_EXAMPLE,
        },
    )
    ident = fields.Str(
        data_key="id",
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    schemaId = fields.Str(
        metadata={
            "description": "Schema identifier within credential definition identifier",
            "example": ":".join(INDY_CRED_DEF_ID_EXAMPLE.split(":")[3:-1]),
        }
    )
    typ = fields.Constant(
        constant="CL",
        data_key="type",
        metadata={
            "description": "Signature type: CL for Camenisch-Lysyanskaya",
            "example": "CL",
        },
    )
    tag = fields.Str(
        metadata={
            "description": "Tag within credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE.split(":")[-1],
        }
    )
    value = fields.Nested(
        CredDefValueSchema(),
        metadata={"description": "Credential definition primary and revocation values"},
    )
