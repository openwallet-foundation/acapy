"""Anoncreds cred def OpenAPI validators"""
from typing import Any, Dict, List, Optional
from typing_extensions import Literal

from anoncreds import RevocationRegistryDefinition, RevocationStatusList
from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf

from ...messaging.models.base import BaseModel, BaseModelSchema


class RevRegDefValue(BaseModel):
    """RevRegDefValue model."""

    class Meta:
        """RevRegDefValue metadata."""

        schema_class = "RevRegDefValueSchema"

    def __init__(
        self,
        public_keys: dict,
        max_cred_num: int,
        tails_location: str,
        tails_hash: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.public_keys = public_keys
        self.max_cred_num = max_cred_num
        self.tails_location = tails_location
        self.tails_hash = tails_hash


class RevRegDefValueSchema(BaseModelSchema):
    """RevRegDefValue schema."""

    class Meta:
        """RevRegDefValueSchema metadata."""

        model_class = RevRegDefValue
        unknown = EXCLUDE

    public_keys = fields.Dict(data_key="publicKeys")
    max_cred_num = fields.Int(data_key="maxCredNum")
    tails_location = fields.Str(data_key="tailsLocation")
    tails_hash = fields.Str(data_key="tailsHash")


class RevRegDef(BaseModel):
    """RevRegDef"""

    class Meta:
        """RevRegDef metadata."""

        schema_class = "RevRegDefSchema"

    def __init__(
        self,
        issuer_id: str,
        type: Literal["CL_ACCUM"],
        cred_def_id: str,
        tag: str,
        value: RevRegDefValue,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.type = type
        self.cred_def_id = cred_def_id
        self.tag = tag
        self.value = value

    @classmethod
    def from_native(cls, rev_reg_def: RevocationRegistryDefinition):
        """Convert a native revocation registry definition to a RevRegDef object."""
        return cls.deserialize(rev_reg_def.to_json())

    def to_native(self):
        """Convert to native anoncreds revocation registry definition."""
        return RevocationRegistryDefinition.load(self.serialize())


class RevRegDefSchema(BaseModelSchema):
    """RevRegDefSchema."""

    class Meta:
        """RevRegDefSchema metadata."""

        model_class = RevRegDef
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
    )
    type = fields.Str(data_key="revocDefType")
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        data_key="credDefId",
    )
    tag = fields.Str(description="tag for the revocation registry definition")
    value = fields.Nested(RevRegDefValueSchema())


class RevRegDefState(BaseModel):
    """RevRegDefState."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"

    class Meta:
        """RevRegDefState metadata."""

        schema_class = "RevRegDefStateSchema"

    def __init__(
        self,
        state: str,
        revocation_registry_definition_id: str,
        revocation_registry_definition: RevRegDef,
    ):
        self.state = state
        self.revocation_registry_definition_id = revocation_registry_definition_id
        self.revocation_registry_definition = revocation_registry_definition


class RevRegDefStateSchema(BaseModelSchema):
    """RevRegDefStateSchema."""

    class Meta:
        """RevRegDefStateSchema metadata."""

        model_class = RevRegDefState
        unknown = EXCLUDE

    state = fields.Str(
        validate=OneOf(
            [
                RevRegDefState.STATE_FINISHED,
                RevRegDefState.STATE_FAILED,
                RevRegDefState.STATE_ACTION,
                RevRegDefState.STATE_WAIT,
            ]
        )
    )
    revocation_registry_definition_id = fields.Str(
        description="revocation registry definition id"
    )
    revocation_registry_definition = fields.Nested(
        RevRegDefSchema(), description="revocation registry definition"
    )


class RevRegDefResult(BaseModel):
    """Cred def result."""

    class Meta:
        """RevRegDefResult metadata."""

        schema_class = "RevRegDefResultSchema"

    def __init__(
        self,
        job_id: Optional[str],
        revocation_registry_definition_state: RevRegDefState,
        registration_metadata: dict,
        revocation_registry_definition_metadata: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.revocation_registry_definition_state = revocation_registry_definition_state
        self.registration_metadata = registration_metadata
        self.revocation_registry_definition_metadata = (
            revocation_registry_definition_metadata
        )

    @property
    def rev_reg_def_id(self):
        return (
            self.revocation_registry_definition_state.revocation_registry_definition_id
        )

    @property
    def rev_reg_def(self):
        return self.revocation_registry_definition_state.revocation_registry_definition


class RevRegDefResultSchema(BaseModelSchema):
    """Cred def result schema."""

    class Meta:
        """RevRegDefResultSchema metadata."""

        model_class = RevRegDefResult
        unknown = EXCLUDE

    job_id = fields.Str()
    revocation_registry_definition_state = fields.Nested(RevRegDefStateSchema())
    registration_metadata = fields.Dict()
    # For indy, revocation_registry_definition_metadata will contain the seqNo
    revocation_registry_definition_metadata = fields.Dict()


class AnonCredsRegistryGetRevocationRegistryDefinition(BaseModel):
    """AnonCredsRegistryGetRevocationRegistryDefinition"""

    class Meta:
        """AnonCredsRegistryGetRevocationRegistryDefinition metadata."""

        schema_class = "AnonCredsRegistryGetRevocationRegistryDefinitionSchema"

    def __init__(
        self,
        revocation_registry: RevRegDef,
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

    revocation_registry = fields.Nested(RevRegDefSchema())
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
        )
    )


class RevList(BaseModel):
    """RevList."""

    class Meta:
        """RevList metadata."""

        schema_class = "RevStatusListSchema"

    def __init__(
        self,
        issuer_id: str,
        rev_reg_def_id: str,
        revocation_list: List[int],
        current_accumulator: str,
        timestamp: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.issuer_id = issuer_id
        self.rev_reg_def_id = rev_reg_def_id
        self.revocation_list = revocation_list
        self.current_accumulator = current_accumulator
        self.timestamp = timestamp

    @classmethod
    def from_native(cls, rev_list: RevocationStatusList):
        """Convert from native revocation list."""
        return cls.deserialize(rev_list.to_json())

    def to_native(self):
        """Convert to native revocation list."""
        return RevocationStatusList.load(self.serialize())


class RevListSchema(BaseModelSchema):
    """RevListSchema."""

    class Meta:
        """RevListSchema metadata."""

        model_class = RevList
        unknown = EXCLUDE

    issuer_id = fields.Str(
        description="Issuer Identifier of the credential definition or schema",
        data_key="issuerId",
    )
    rev_reg_def_id = fields.Str(
        description="",
        data_key="revRegDefId",
    )
    revocation_list = fields.List(
        fields.Int(),
        description="Bit list representing revoked credentials",
        data_key="revocationList",
    )
    current_accumulator = fields.Str(data_key="currentAccumulator")
    timestamp = fields.Int(
        description="Timestamp at which revocation list is applicable",
        required=False,
    )


class RevListState(BaseModel):
    """RevListState."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"

    class Meta:
        """RevListState metadata."""

        schema_class = "RevListStateSchema"

    def __init__(
        self,
        state: str,
        revocation_list: RevList,
    ):
        self.state = state
        self.revocation_list = revocation_list


class RevListStateSchema(BaseModelSchema):
    """RevListStateSchema."""

    class Meta:
        """RevListStateSchema metadata."""

        model_class = RevListState
        unknown = EXCLUDE

    state = fields.Str(
        validate=OneOf(
            [
                RevListState.STATE_FINISHED,
                RevListState.STATE_FAILED,
                RevListState.STATE_ACTION,
                RevListState.STATE_WAIT,
            ]
        )
    )
    revocation_list = fields.Nested(RevListSchema(), description="revocation list")


class RevListResult(BaseModel):
    """Cred def result."""

    class Meta:
        """RevListResult metadata."""

        schema_class = "RevListResultSchema"

    def __init__(
        self,
        job_id: Optional[str],
        revocation_list_state: RevListState,
        registration_metadata: dict,
        revocation_list_metadata: dict,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.job_id = job_id
        self.revocations_list_state = revocation_list_state
        self.registration_metadata = registration_metadata
        self.revocation_list_metadata = revocation_list_metadata

    @property
    def rev_reg_def_id(self):
        return self.revocation_list_state.revocation_list_id


class RevListResultSchema(BaseModelSchema):
    """Cred def result schema."""

    class Meta:
        """RevListResultSchema metadata."""

        model_class = RevListResult
        unknown = EXCLUDE

    job_id = fields.Str()
    revocation_list_state = fields.Nested(RevListStateSchema())
    registration_metadata = fields.Dict()
    # For indy, revocation_list_metadata will contain the seqNo
    revocation_list_metadata = fields.Dict()


class GetRevListResult(BaseModel):
    """GetRevListResult"""

    class Meta:
        """GetRevListResult metadata."""

        schema_class = "GetRevListResultSchema"

    def __init__(
        self,
        revocation_list: RevList,
        resolution_metadata: Dict[str, Any],
        revocation_registry_metadata: Dict[str, Any],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.revocation_list = revocation_list
        self.resolution_metadata = resolution_metadata
        self.revocation_registry_metadata = revocation_registry_metadata


class GetRevListResultSchema(BaseModelSchema):
    """GetRevListResultSchema"""

    class Meta:
        """GetRevListResultSchema metadata."""

        model_class = GetRevListResult
        unknown = EXCLUDE

    revocation_list = fields.Nested(RevListSchema)
    resolution_metadata = fields.Str()
    revocation_registry_metadata = fields.Dict()
