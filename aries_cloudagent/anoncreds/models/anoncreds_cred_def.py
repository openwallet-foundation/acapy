"""Anoncreds cred def OpenAPI validators"""
from typing import Any, Dict, List, Optional
from typing_extensions import Literal

from marshmallow import EXCLUDE, Schema, fields

from aries_cloudagent.anoncreds.models.anoncreds_valid import (
    ANONCREDS_SCHEMA_ID,
    ANONCREDS_VERSION,
)
from aries_cloudagent.messaging.models.base import BaseModel, BaseModelSchema
from aries_cloudagent.messaging.valid import (
    GENERIC_DID,
    INDY_CRED_DEF_ID,
    NUM_STR_WHOLE,
)

from ...messaging.models.openapi import OpenAPISchema
from .anoncreds_schema import AnonCredsSchema


class PrimarySchema(BaseModel):
    """PrimarySchema"""

    class Meta:
        """PrimarySchema metadata."""

        schema_class = "PrimarySchemaSchema"

    def __init__(self, n: str, s: str, r: dict, rctxt: str, z: str, **kwargs):
        super().__init__(**kwargs)
        self.n = n
        self.s = s
        self.r = r
        self.rctxt = rctxt
        self.z = z


class PrimarySchemaSchema(BaseModelSchema):
    """Parameters and validators for credential definition primary."""

    class Meta:
        """PrimarySchema metadata."""

        model_class = AnonCredsSchema
        unknown = EXCLUDE

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


# TODO: determine types for `primary` and `revocation`
class AnonCredsCredentialDefinitionValue(BaseModel):
    """AnonCredsCredentialDefinitionValue"""

    class Meta:
        """AnonCredsCredentialDefinitionValue metadata."""

        schema_class = "AnonCredsCredentialDefinitionValueSchema"

    def __init__(self, primary: PrimarySchema, **kwargs):
        super().__init__(**kwargs)
        self.primary = primary

    # revocation: Optional[Any]


class AnonCredsCredentialDefinitionValueSchema(BaseModelSchema):
    """Parameters and validators for credential definition value."""

    class Meta:
        """AnonCredsCredentialDefinitionValueSchema metadata."""

        model_class = AnonCredsCredentialDefinitionValue
        unknown = EXCLUDE

    primary = fields.Nested(PrimarySchemaSchema())


class AnonCredsCredentialDefinition(BaseModel):
    """AnonCredsCredentialDefinition"""

    class Meta:
        """AnonCredsCredentialDefinition metadata."""

        schema_class = "AnonCredsCredentialDefinitionSchema"

    def __init__(
        self,
        issuer_id: str,
        schema_id: str,
        type: Literal["CL"],
        tag: str,
        value: AnonCredsCredentialDefinitionValue,
        **kwargs
    ):
        self.issuer_id = issuer_id
        self.schema_id = schema_id
        self.type = type
        self.tag = tag
        self.value = value


class AnonCredsCredentialDefinitionSchema(BaseModelSchema):
    """AnonCredsCredentialDefinitionSchema"""

    class Meta:
        """AnonCredsCredentialDefinitionSchema metadata."""

        model_class = AnonCredsCredentialDefinition
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
        data_key="issuerId",
    )  # TODO: get correct validator
    schema_id = fields.Str(
        data_key="schemaId", description="Schema identifier", **ANONCREDS_SCHEMA_ID
    )
    type = fields.Str()
    tag = fields.Str(
        description="""The tag value passed in by the Issuer to
         an AnonCred's Credential Definition create and store implementation."""
    )
    value = fields.Nested(AnonCredsCredentialDefinitionValueSchema())


class AnonCredsRegistryGetCredentialDefinition(BaseModel):
    """AnonCredsRegistryGetCredentialDefinition"""

    class Meta:
        """AnonCredsRegistryGetCredentialDefinition metadata."""

        schema_class = "AnonCredsRegistryGetCredentialDefinitionSchema"

    def __init__(
        self,
        credential_definition: AnonCredsCredentialDefinition,
        credential_definition_id: str,
        resolution_metadata: dict,
        credential_definition_metadata: dict,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.credential_definition = credential_definition
        self.credential_definition_id = credential_definition_id
        self.resolution_metadata = resolution_metadata
        self.credential_definition_metadata = credential_definition_metadata


class AnonCredsRegistryGetCredentialDefinitionSchema(BaseModelSchema):
    """Parameters and validators for credential definition list response."""

    class Meta:
        """AnonCredsRegistryGetCredentialDefinitionSchema metadata."""

        model_class = AnonCredsRegistryGetCredentialDefinition
        unknown = EXCLUDE

    credential_definition_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
    )
    credential_definition = fields.Nested(AnonCredsCredentialDefinitionSchema())
    resolution_metadata = fields.Dict()
    credential_definition_metadata = fields.Dict()


class AnonCredsRevocationRegistryDefinition(BaseModel):
    """AnonCredsRevocationRegistryDefinition"""

    class Meta:
        """AnonCredsRevocationRegistryDefinition metadata."""

        schema_class = "AnonCredsRevocationRegistryDefinitionSchema"

    def __init__(
        self,
        issuer_id: str,
        type: Literal["CL_ACCUM"],
        cred_def_id: str,
        tag: str,
        # TODO: determine type for `publicKeys`
        public_keys: Any,
        max_cred_num: int,
        tails_Location: str,
        tails_hash: str,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.type = type
        self.cred_def_id = cred_def_id
        self.tag = tag
        self.public_keys = public_keys
        self.max_cred_num = max_cred_num
        self.tails_location = tails_Location
        self.tails_hash = tails_hash


class AnonCredsRevocationRegistryDefinitionSchema(BaseModelSchema):
    """AnonCredsRevocationRegistryDefinitionSchema"""

    class Meta:
        """AnonCredsRevocationRegistryDefinitionSchema metadata."""

        model_class = AnonCredsRevocationRegistryDefinition
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
        data_key="issuerId",
    )  # TODO: get correct validator
    type = fields.Str()
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        **INDY_CRED_DEF_ID,
        data_key="credDefId",
    )
    tag = fields.Str(description="""""")
    # TODO: type for public key
    public_keys = fields.Str(data_key="publicKeys")
    max_cred_num = fields.Int(data_key="maxCredNum")
    tails_location = fields.Str(data_key="tailsLocation")
    tails_hash = fields.Str(data_key="tailsHash")


class AnonCredsRegistryGetRevocationRegistryDefinition(BaseModel):
    """AnonCredsRegistryGetRevocationRegistryDefinition"""

    class Meta:
        """AnonCredsRegistryGetRevocationRegistryDefinition metadata."""

        schema_class = "AnonCredsRegistryGetRevocationRegistryDefinitionSchema"

    def __init__(
        self,
        revocation_registry: AnonCredsRevocationRegistryDefinition,
        revocation_registry_id: str,
        resolution_metadata: Dict[str, Any],
        revocation_registry_metadata: Dict[str, Any],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.revocation_registry = revocation_registry
        self.revocation_registry_id = revocation_registry_id
        self.resolution_metadata = resolution_metadata
        self.revocation_registry_metadata = revocation_registry_metadata


class AnonCredsRegistryGetRevocationRegistryDefinitionSchema(BaseModelSchema):
    class Meta:
        """AnonCredsRegistryGetRevocationRegistryDefinitionSchema metadata."""

        model_class = AnonCredsRegistryGetRevocationRegistryDefinition
        unknown = EXCLUDE

    revocation_registry = fields.Nested(AnonCredsRevocationRegistryDefinitionSchema())
    revocation_registry_id = fields.Str()
    resolution_metadata = fields.Dict()
    revocation_registry_metadata = fields.Dict()


class AnonCredsRevocationList(BaseModel):
    """AnonCredsRevocationList"""

    class Meta:
        """AnonCredsRevocationList metadata."""

        schema_class = "AnonCredsRevocationListSchema"

    def __init__(
        self,
        issuer_id: str,
        rev_reg_id: str,
        revocation_list: List[int],
        current_accumulator: str,
        timestamp: int,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.rev_reg_id = rev_reg_id
        self.revocation_list = revocation_list
        self.current_accumulator = current_accumulator
        self.timestamp = timestamp


class AnonCredsRevocationListSchema(BaseModelSchema):
    """AnonCredsRevocationListSchema"""

    class Meta:
        """AnonCredsRevocationListSchema metadata."""

        model_class = AnonCredsRevocationList
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        **GENERIC_DID,
        data_key="issuerId",
    )  # TODO: get correct validator
    rev_reg_id = fields.Str(
        description="",
        **GENERIC_DID,
        data_key="revRegId",
    )  # TODO: get correct validator
    revocation_list = fields.List(
        fields.Str(description=""), description="", data_key="revocationList"
    )
    current_accumulator = fields.Str(data_key="currentAccumulator")
    timestamp = fields.Int()


class AnonCredsRegistryGetRevocationList(BaseModel):
    """AnonCredsRegistryGetRevocationList"""

    class Meta:
        """AnonCredsRegistryGetRevocationList metadata."""

        schema_class = "AnonCredsRegistryGetRevocationListSchema"

    def __init__(
        self,
        revocation_list: AnonCredsRevocationList,
        resolution_metadata: Dict[str, Any],
        revocation_registry_metadata: Dict[str, Any],
        **kwargs
    ):
        super().__init__(**kwargs)
        self.revocation_list = revocation_list
        self.resolution_metadata = resolution_metadata
        self.revocation_registry_metadata = revocation_registry_metadata


class AnonCredsRegistryGetRevocationListSchema(BaseModelSchema):
    """AnonCredsRegistryGetRevocationListSchema"""

    class Meta:
        """AnonCredsRegistryGetRevocationListSchema metadata."""

        model_class = AnonCredsRegistryGetRevocationList
        unknown = EXCLUDE

    revocation_list = fields.Nested(AnonCredsRevocationListSchema)
    resolution_metadata = fields.Str()
    revocation_registry_metadata = fields.Dict()
