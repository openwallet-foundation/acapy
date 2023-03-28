"""Anoncreds cred def OpenAPI validators"""
from typing import Any, Dict, List, Optional
from typing_extensions import Literal
from anoncreds import CredentialDefinition

from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf

from aries_cloudagent.messaging.models.base import BaseModel, BaseModelSchema
from aries_cloudagent.messaging.valid import (
    GENERIC_DID,
    INDY_CRED_DEF_ID,
    NUM_STR_WHOLE,
)


class CredDefValuePrimary(BaseModel):
    """PrimarySchema"""

    class Meta:
        """PrimarySchema metadata."""

        schema_class = "CredDefValuePrimarySchema"

    def __init__(self, n: str, s: str, r: dict, rctxt: str, z: str, **kwargs):
        super().__init__(**kwargs)
        self.n = n
        self.s = s
        self.r = r
        self.rctxt = rctxt
        self.z = z


class CredDefValuePrimarySchema(BaseModelSchema):
    """Cred def value primary schema."""

    class Meta:
        """CredDefValuePrimarySchema metadata."""

        model_class = CredDefValuePrimary
        unknown = EXCLUDE

    n = fields.Str(**NUM_STR_WHOLE)
    s = fields.Str(**NUM_STR_WHOLE)
    r = fields.Dict()
    rctxt = fields.Str(**NUM_STR_WHOLE)
    z = fields.Str(**NUM_STR_WHOLE)


class CredDefValueRevocation(BaseModel):
    """Cred def value revocation."""

    class Meta:
        """CredDefValueRevocation metadata."""

        schema_class = "CredDefValueRevocationSchema"

    def __init__(
        self,
        g: str,
        g_dash: str,
        h: str,
        h0: str,
        h1: str,
        h2: str,
        htilde: str,
        h_cap: str,
        u: str,
        pk: str,
        y: str,
    ):
        self.g = g
        self.g_dash = g_dash
        self.h = h
        self.h0 = h0
        self.h1 = h1
        self.h2 = h2
        self.htilde = htilde
        self.h_cap = h_cap
        self.u = u
        self.pk = pk
        self.y = y


class CredDefValueRevocationSchema(BaseModelSchema):
    """Cred def value revocation schema."""

    class Meta:
        model_class = CredDefValueRevocation
        unknown = EXCLUDE

    g = fields.Str(example="1 1F14F&ECB578F 2 095E45DDF417D")
    g_dash = fields.Str(example="1 1D64716fCDC00C 1 0C781960FA66E3D3 2 095E45DDF417D")
    h = fields.Str(example="1 16675DAE54BFAE8 2 095E45DD417D")
    h0 = fields.Str(example="1 21E5EF9476EAF18 2 095E45DDF417D")
    h1 = fields.Str(example="1 236D1D99236090 2 095E45DDF417D")
    h2 = fields.Str(example="1 1C3AE8D1F1E277 2 095E45DDF417D")
    htilde = fields.Str(example="1 1D8549E8C0F8 2 095E45DDF417D")
    h_cap = fields.Str(example="1 1B2A32CF3167 1 2490FEBF6EE55 1 0000000000000000")
    u = fields.Str(example="1 0C430AAB2B4710 1 1CB3A0932EE7E 1 0000000000000000")
    pk = fields.Str(example="1 142CD5E5A7DC 1 153885BD903312 2 095E45DDF417D")
    y = fields.Str(example="1 153558BD903312 2 095E45DDF417D 1 0000000000000000")


class CredDefValue(BaseModel):
    """Cred def value."""

    class Meta:
        """CredDefValue metadata."""

        schema_class = "CredDefValueSchema"

    def __init__(
        self,
        primary: CredDefValuePrimary,
        revocation: Optional[CredDefValueRevocation] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.primary = primary
        self.revocation = revocation


class CredDefValueSchema(BaseModelSchema):
    """Cred def value schema."""

    class Meta:
        """CredDefValueSchema metadata."""

        model_class = CredDefValue
        unknown = EXCLUDE

    primary = fields.Nested(
        CredDefValuePrimarySchema(),
        description="Primary value for credential definition",
    )
    revocation = fields.Nested(
        CredDefValueRevocationSchema(),
        description="Revocation value for credential definition",
        required=False,
    )


class CredDef(BaseModel):
    """AnonCredsCredDef"""

    class Meta:
        """AnonCredsCredDef metadata."""

        schema_class = "CredDefSchema"

    def __init__(
        self,
        issuer_id: str,
        schema_id: str,
        type: Literal["CL"],
        tag: str,
        value: CredDefValue,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.schema_id = schema_id
        self.type = type
        self.tag = tag
        self.value = value

    @classmethod
    def from_native(cls, cred_def: CredentialDefinition):
        """Convert a native credential definition to a CredDef object."""
        return cls.deserialize(cred_def.to_json())

    def to_native(self):
        """Convert to native anoncreds credential definition."""
        return CredentialDefinition.load(self.serialize())


class CredDefSchema(BaseModelSchema):
    """CredDefSchema."""

    class Meta:
        """CredDefSchema metadata."""

        model_class = CredDef
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
    )
    schema_id = fields.Str(data_key="schemaId", description="Schema identifier")
    type = fields.Str(validate=OneOf(["CL"]))
    tag = fields.Str(
        description="""The tag value passed in by the Issuer to
         an AnonCred's Credential Definition create and store implementation."""
    )
    value = fields.Nested(CredDefValueSchema())


class CredDefState(BaseModel):
    """CredDefState."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"

    class Meta:
        """CredDefState metadata."""

        schema_class = "CredDefStateSchema"

    def __init__(
        self, state: str, credential_definition_id: str, credential_definition: CredDef
    ):
        self.state = state
        self.credential_definition_id = credential_definition_id
        self.credential_definition = credential_definition


class CredDefStateSchema(BaseModelSchema):
    """CredDefStateSchema."""

    class Meta:
        """CredDefStateSchema metadata."""

        model_class = CredDefState
        unknown = EXCLUDE

    state = fields.Str(
        validate=OneOf(
            [
                CredDefState.STATE_FINISHED,
                CredDefState.STATE_FAILED,
                CredDefState.STATE_ACTION,
                CredDefState.STATE_WAIT,
            ]
        )
    )
    credential_definition_id = fields.Str(description="credential definition id")
    credential_definition = fields.Nested(
        CredDefSchema(), description="credential definition"
    )


class CredDefResult(BaseModel):
    """Cred def result."""

    class Meta:
        """CredDefResult metadata."""

        schema_class = "CredDefResultSchema"

    def __init__(
        self,
        job_id: Optional[str],
        credential_definition_state: CredDefState,
        registration_metadata: dict,
        credential_definition_metadata: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.credential_definition_state = credential_definition_state
        self.registration_metadata = registration_metadata
        self.credential_definition_metadata = credential_definition_metadata


class CredDefResultSchema(BaseModelSchema):
    """Cred def result schema."""

    class Meta:
        """CredDefResultSchema metadata."""

        model_class = CredDefResult
        unknown = EXCLUDE

    job_id = fields.Str()
    credential_definition_state = fields.Nested(CredDefStateSchema())
    registration_metadata = fields.Dict()
    # For indy, credential_definition_metadata will contain the seqNo
    credential_definition_metadata = fields.Dict()


class GetCredDefResult(BaseModel):
    """Get cred def result."""

    class Meta:
        """AnonCredsRegistryGetCredDef metadata."""

        schema_class = "GetCredDefResultSchema"

    def __init__(
        self,
        credential_definition_id: str,
        credential_definition: CredDef,
        resolution_metadata: dict,
        credential_definition_metadata: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.credential_definition_id = credential_definition_id
        self.credential_definition = credential_definition
        self.resolution_metadata = resolution_metadata
        self.credential_definition_metadata = credential_definition_metadata


class GetCredDefResultSchema(BaseModelSchema):
    """GetCredDefResultSchema."""

    class Meta:
        """GetCredDefResultSchema metadata."""

        model_class = GetCredDefResult
        unknown = EXCLUDE

    credential_definition_id = fields.Str(description="credential definition id")
    credential_definition = fields.Nested(
        CredDefSchema(), description="credential definition"
    )
    resolution_metadata = fields.Dict()
    credential_definitions_metadata = fields.Dict()


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
        **kwargs,
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
        **kwargs,
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


class AnonCredsRegistryGetRevocationRegistryDefinitions(BaseModel):
    """AnonCredsRegistryGetRevocationRegistryDefinitions"""

    class Meta:
        """AnonCredsRegistryGetRevocationRegistryDefinitions metadata."""

        schema_class = "AnonCredsRegistryGetRevocationRegistryDefinitionsSchema"

    def __init__(self, revocation_definition_ids: list, **kwargs):
        super().__init__(**kwargs)
        self.revocation_definition_ids = revocation_definition_ids


class AnonCredsRegistryGetRevocationRegistryDefinitionsSchema(BaseModelSchema):
    """AnonCredsRegistryGetRevocationRegistryDefinitionsSchema"""

    class Meta:
        """AnonCredsRegistryGetRevocationRegistryDefinitionsSchema metadata"""

        model_class = AnonCredsRegistryGetRevocationRegistryDefinitions
        unknown = EXCLUDE

    revocation_definition_ids = fields.List(
        fields.Str(
            data_key="revocation_definition_ids",
            description="credential definition identifiers",
            **INDY_CRED_DEF_ID,
        )
    )


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
        **kwargs,
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
        **kwargs,
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
