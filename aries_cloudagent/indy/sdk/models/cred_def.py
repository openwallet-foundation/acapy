"""Schema artifacts."""

from marshmallow import fields, Schema

from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import INDY_CRED_DEF_ID, INDY_VERSION, NUM_STR_WHOLE


class CredDefValuePrimarySchema(OpenAPISchema):
    """Cred def value primary schema."""

    n = fields.Str(**NUM_STR_WHOLE)
    s = fields.Str(**NUM_STR_WHOLE)
    r = fields.Nested(
        Schema.from_dict(
            {
                "master_secret": fields.Str(**NUM_STR_WHOLE),
                "number": fields.Str(**NUM_STR_WHOLE),
                "remainder": fields.Str(**NUM_STR_WHOLE),
            }
        )
    )
    rctxt = fields.Str(**NUM_STR_WHOLE)
    z = fields.Str(**NUM_STR_WHOLE)


class CredDefValueRevocationSchema(OpenAPISchema):
    """Cred def value revocation schema."""

    g = fields.Str()
    g_dash = fields.Str()
    h = fields.Str()
    h0 = fields.Str()
    h1 = fields.Str()
    h2 = fields.Str()
    htilde = fields.Str()
    h_cap = fields.Str()
    u = fields.Str()
    pk = fields.Str()
    y = fields.Str()


class CredDefValueSchema(OpenAPISchema):
    """Cred def value schema."""

    primary = fields.Nested(
        CredDefValuePrimarySchema(),
        description="Primary value for credential definition",
    )
    revocation = fields.Nested(
        CredDefValueRevocationSchema(),
        description="Revocation value for credential definition",
    )


class CredentialDefinitionSchema(OpenAPISchema):
    """Marshmallow schema for indy cred def."""

    ver = fields.Str(description="Node protocol version", **INDY_VERSION)
    ident = fields.Str(
        description="Credential definition identifier",
        data_key="id",
        **INDY_CRED_DEF_ID,
    )
    schemaId = fields.Str(
        description="Schema identifier within credential definition identifier",
        example=":".join(INDY_CRED_DEF_ID["example"].split(":")[3:-1]),  # long or short
    )
    typ = fields.Constant(
        constant="CL",
        description="Signature type: CL for Camenisch-Lysyanskaya",
        data_key="type",
        example="CL",
    )
    tag = fields.Str(
        description="Tag within credential definition identifier",
        example=INDY_CRED_DEF_ID["example"].split(":")[-1],
    )
    value = fields.Nested(
        CredDefValueSchema(),
        description="Credential definition primary and revocation values",
    )
