"""Schema artifacts."""

from marshmallow import fields, Schema

from ...messaging.models.openapi import OpenAPISchema
from ...messaging.valid import IndyCredDefId, IndyVersion, NumericStrWhole


class CredDefValuePrimarySchema(OpenAPISchema):
    """Cred def value primary schema."""

    n = fields.Str(
        validate=NumericStrWhole(), metadata={"example": NumericStrWhole.EXAMPLE}
    )
    s = fields.Str(
        validate=NumericStrWhole(), metadata={"example": NumericStrWhole.EXAMPLE}
    )
    r = fields.Nested(
        Schema.from_dict(
            {
                "master_secret": fields.Str(
                    validate=NumericStrWhole(),
                    metadata={"example": NumericStrWhole.EXAMPLE},
                ),
                "number": fields.Str(
                    validate=NumericStrWhole(),
                    metadata={"example": NumericStrWhole.EXAMPLE},
                ),
                "remainder": fields.Str(
                    validate=NumericStrWhole(),
                    metadata={"example": NumericStrWhole.EXAMPLE},
                ),
            }
        ),
        metadata={"name": "CredDefValuePrimaryRSchema"},
    )
    rctxt = fields.Str(
        validate=NumericStrWhole(), metadata={"example": NumericStrWhole.EXAMPLE}
    )
    z = fields.Str(
        validate=NumericStrWhole(), metadata={"example": NumericStrWhole.EXAMPLE}
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
        validate=IndyVersion(),
        metadata={
            "description": "Node protocol version",
            "example": IndyVersion.EXAMPLE,
        },
    )
    ident = fields.Str(
        data_key="id",
        validate=IndyCredDefId(),
        metadata={
            "description": "Credential definition identifier",
            "example": IndyCredDefId.EXAMPLE,
        },
    )
    schemaId = fields.Str(
        metadata={
            "description": "Schema identifier within credential definition identifier",
            "example": ":".join(IndyCredDefId.EXAMPLE.split(":")[3:-1]),
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
            "example": IndyCredDefId.EXAMPLE.split(":")[-1],
        }
    )
    value = fields.Nested(
        CredDefValueSchema(),
        metadata={"description": "Credential definition primary and revocation values"},
    )
