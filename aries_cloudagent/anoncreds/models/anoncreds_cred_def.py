"""Anoncreds cred def OpenAPI validators"""
from marshmallow import Schema, fields
from aries_cloudagent.anoncreds.models.anoncreds_valid import ANONCREDS_SCHEMA_ID,ANONCREDS_VERSION

from aries_cloudagent.messaging.valid import GENERIC_DID, INDY_CRED_DEF_ID, NUM_STR_WHOLE

from ...messaging.models.openapi import OpenAPISchema


# TODO: determine types for `primary` and `revocation`
class AnonCredsCredentialDefinitionValue:
    """AnonCredsCredentialDefinitionValue"""

    primary: Any
    revocation: Optional[Any]



class AnonCredsCredentialDefinition:
    """AnonCredsCredentialDefinition"""

    issuerId: str
    schemaId: str
    type: Literal["CL"]
    tag: str
    value: AnonCredsCredentialDefinitionValue


class AnonCredsRegistryGetCredentialDefinition:
    """AnonCredsRegistryGetCredentialDefinition"""

    credential_definition: AnonCredsCredentialDefinition
    credential_definition_id: str
    resolution_metadata: Dict[str, Any]
    credential_definition_metadata: Dict[str, Any]


class AnonCredsRevocationRegistryDefinition:
    """AnonCredsRevocationRegistryDefinition"""

    issuerId: str
    type: Literal["CL_ACCUM"]
    credDefId: str
    tag: str
    # TODO: determine type for `publicKeys`
    publicKeys: Any
    maxCredNum: int
    tailsLocation: str
    tailsHash: str


class AnonCredsRegistryGetRevocationRegistryDefinition:
    """AnonCredsRegistryGetRevocationRegistryDefinition"""

    revocation_registry: AnonCredsRevocationRegistryDefinition
    revocation_registry_id: str
    resolution_metadata: Dict[str, Any]
    revocation_registry_metadata: Dict[str, Any]

class PrimarySchema(OpenAPISchema):
    """Parameters and validators for credential definition primary."""

    n = fields.Str(**NUM_STR_WHOLE)
    s = fields.Str(**NUM_STR_WHOLE)
    r = fields.Nested(
        Schema.from_dict(
            {
                "master_secret": fields.Str(**NUM_STR_WHOLE),
                "number": fields.Str(**NUM_STR_WHOLE),
                "remainder": fields.Str(**NUM_STR_WHOLE),
            }
        ),
        name="CredDefValuePrimaryRSchema",
    )
    rctxt = fields.Str(**NUM_STR_WHOLE)
    z = fields.Str(**NUM_STR_WHOLE)


class CredDefValueSchema(OpenAPISchema):
    """Parameters and validators for credential definition value."""

    primary = fields.Nested(PrimarySchema())



class CredDefSchema(OpenAPISchema):
    """Parameters and validators for credential definition."""

    tag = fields.Str(
        description="""The tag value passed in by the Issuer to
         an AnonCred's Credential Definition create and store implementation."""
    )
    schemaId = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    issuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator
    supportRevocation = fields.Bool()
    revocationRegistrySize = fields.Int()


class CredDefPostOptionsSchema(OpenAPISchema):
    """Parameters and validators for credential definition options."""

    endorserConnectionId = fields.Str()
    supportRevocation = fields.Bool()
    revocationRegistrySize = fields.Int()


class CredDefPostQueryStringSchema(OpenAPISchema):
    """Parameters and validators for query string in create credential definition."""

    credentialDefinition = fields.Nested(CredDefSchema())
    options = fields.Nested(CredDefPostOptionsSchema())


class CredDefsQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential definition list query."""

    credentialDefinitionId = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    issuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator
    schemaId = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    schemaIssuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator
    schemaName = fields.Str(
        description="Schema name",
        example=ANONCREDS_SCHEMA_ID["example"].split(":")[2],
    )
    schemaVersion = fields.Str(description="Schema version", **ANONCREDS_VERSION)


class CredDefResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition response."""

    issuerId = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
    )  # TODO: get correct validator
    schemaId = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    tag = fields.Str(
        description="The tag value passed in by the Issuer to an\
            AnonCred's Credential Definition create and store implementation."
    )
    value = fields.Nested(CredDefValueSchema())
    # registration_metadata = fields.Bool()
    # revocationRegistrySize = fields.Int()


class CredDefState(OpenAPISchema):
    """Parameters and validators for credential definition state."""

    state = fields.Str()  # TODO: create validator for only possible states
    credential_definition_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    credential_definition = fields.Nested(CredDefResponseSchema())


class PostCredDefResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition create response."""

    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefState())
    registration_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class GetCredDefResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition list response."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    credential_definition = fields.Nested(CredDefResponseSchema())
    resolution_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class GetCredDefsResponseSchema(OpenAPISchema):
    """Parameters and validators for credential definition list all response."""

    credential_definition_id = fields.Str()