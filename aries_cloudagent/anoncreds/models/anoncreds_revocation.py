"""Anoncreds cred def OpenAPI validators."""

from typing import Any, Dict, List, Optional

from anoncreds import RevocationRegistryDefinition, RevocationStatusList
from marshmallow import EXCLUDE, fields
from marshmallow.validate import OneOf
from typing_extensions import Literal

from aries_cloudagent.messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_ISO8601_DATETIME_EXAMPLE,
    INDY_OR_KEY_DID_EXAMPLE,
    INDY_RAW_PUBLIC_KEY_EXAMPLE,
    INDY_REV_REG_ID_EXAMPLE,
)

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
        """Initialize an instance.

        Args:
            public_keys: Public Keys
            max_cred_num: Max. number of Creds
            tails_location: Tails file location
            tails_hash: Tails file hash

        TODO: update this docstring - Anoncreds-break.

        """
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

    public_keys = fields.Dict(
        data_key="publicKeys", metadata={"example": INDY_RAW_PUBLIC_KEY_EXAMPLE}
    )
    max_cred_num = fields.Int(data_key="maxCredNum", metadata={"example": 777})
    tails_location = fields.Str(
        data_key="tailsLocation",
        metadata={
            "example": "https://tails-server.com/hash/7Qen9RDyemMuV7xGQvp7NjwMSpyHieJyBakycxN7dX7P"
        },
    )
    tails_hash = fields.Str(
        data_key="tailsHash",
        metadata={"example": "7Qen9RDyemMuV7xGQvp7NjwMSpyHieJyBakycxN7dX7P"},
    )


class RevRegDef(BaseModel):
    """RevRegDef."""

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
        """Initialize an instance.

        Args:
            issuer_id: Issuer ID
            type: type
            cred_def_id: Cred Def ID
            tag: Tag
            value: Rev Reg Def Value

        TODO: update this docstring - Anoncreds-break.

        """
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
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        },
        data_key="issuerId",
    )
    type = fields.Str(data_key="revocDefType")
    cred_def_id = fields.Str(
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
        data_key="credDefId",
    )
    tag = fields.Str(
        metadata={
            "description": "tag for the revocation registry definition",
            "example": "default",
        }
    )
    value = fields.Nested(RevRegDefValueSchema())


class RevRegDefState(BaseModel):
    """RevRegDefState."""

    STATE_FINISHED = "finished"
    STATE_FAILED = "failed"
    STATE_ACTION = "action"
    STATE_WAIT = "wait"
    STATE_DECOMMISSIONED = "decommissioned"
    STATE_FULL = "full"

    class Meta:
        """RevRegDefState metadata."""

        schema_class = "RevRegDefStateSchema"

    def __init__(
        self,
        state: str,
        revocation_registry_definition_id: str,
        revocation_registry_definition: RevRegDef,
    ):
        """Initialize an instance.

        Args:
            state: State
            revocation_registry_definition_id: Rev Reg Definition ID
            revocation_registry_definition: Rev Reg Definition

        TODO: update this docstring - Anoncreds-break.

        """
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
                RevRegDefState.STATE_DECOMMISSIONED,
                RevRegDefState.STATE_FULL,
            ]
        )
    )
    revocation_registry_definition_id = fields.Str(
        metadata={
            "description": "revocation registry definition id",
            "example": INDY_REV_REG_ID_EXAMPLE,
        }
    )
    revocation_registry_definition = fields.Nested(
        RevRegDefSchema(), metadata={"description": "revocation registry definition"}
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
        """Initialize an instance.

        Args:
            job_id: Job ID
            revocation_registry_definition_state: Rev Reg Def state
            registration_metadata: Registration metadata
            revocation_registry_definition_metadata: Rev Reg Def metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.job_id = job_id
        self.revocation_registry_definition_state = revocation_registry_definition_state
        self.registration_metadata = registration_metadata
        self.revocation_registry_definition_metadata = (
            revocation_registry_definition_metadata
        )

    @property
    def rev_reg_def_id(self):
        """Revocation Registry Definition ID."""
        return (
            self.revocation_registry_definition_state.revocation_registry_definition_id
        )

    @property
    def rev_reg_def(self):
        """Revocation Registry Definition."""
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


class GetRevRegDefResult(BaseModel):
    """GetRevRegDefResult."""

    class Meta:
        """GetRevRegDefResult metadata."""

        schema_class = "GetRevRegDefResultSchema"

    def __init__(
        self,
        revocation_registry: RevRegDef,
        revocation_registry_id: str,
        resolution_metadata: Dict[str, Any],
        revocation_registry_metadata: Dict[str, Any],
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            revocation_registry: Revocation registry
            revocation_registry_id: Revocation Registry ID
            resolution_metadata: Resolution metadata
            revocation_registry_metadata: Revocation Registry metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.revocation_registry = revocation_registry
        self.revocation_registry_id = revocation_registry_id
        self.resolution_metadata = resolution_metadata
        self.revocation_registry_metadata = revocation_registry_metadata


class GetRevRegDefResultSchema(BaseModelSchema):
    """GetRevRegDefResultSchema."""

    class Meta:
        """GetRevRegDefResultSchema metadata."""

        model_class = GetRevRegDefResult
        unknown = EXCLUDE

    revocation_registry = fields.Nested(RevRegDefSchema())
    revocation_registry_id = fields.Str()
    resolution_metadata = fields.Dict()
    revocation_registry_metadata = fields.Dict()


class RevList(BaseModel):
    """RevList."""

    class Meta:
        """RevList metadata."""

        schema_class = "RevListSchema"

    def __init__(
        self,
        issuer_id: str,
        rev_reg_def_id: str,
        revocation_list: List[int],
        current_accumulator: str,
        timestamp: Optional[int] = None,
        **kwargs,
    ):
        """Initialize an instance.

        Args:
            issuer_id: Job ID
            rev_reg_def_id: Revocation Registry Def. ID
            revocation_list: Revocation list
            current_accumulator: Current accumulator
            timestamp: Timestamp

        TODO: update this docstring - Anoncreds-break.

        """
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
        metadata={
            "description": "Issuer Identifier of the credential definition or schema",
            "example": INDY_OR_KEY_DID_EXAMPLE,
        },
        data_key="issuerId",
    )
    rev_reg_def_id = fields.Str(
        metadata={
            "description": "The ID of the revocation registry definition",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
        data_key="revRegDefId",
    )
    revocation_list = fields.List(
        fields.Int(),
        metadata={
            "description": "Bit list representing revoked credentials",
            "example": [0, 1, 1, 0],
        },
        data_key="revocationList",
    )
    current_accumulator = fields.Str(
        metadata={
            "description": "The current accumulator value",
            "example": "21 118...1FB",
        },
        data_key="currentAccumulator",
    )
    timestamp = fields.Int(
        metadata={
            "description": "Timestamp at which revocation list is applicable",
            "example": INDY_ISO8601_DATETIME_EXAMPLE,
        },
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
        """Initialize an instance.

        Args:
            state: State
            revocation_list: Revocation list

        TODO: update this docstring - Anoncreds-break.

        """
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
    revocation_list = fields.Nested(
        RevListSchema(), metadata={"description": "revocation list"}
    )


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
        """Initialize an instance.

        Args:
            job_id: Job ID
            revocation_list_state: Revocation list state
            registration_metadata: Registration metadata
            revocation_list_metadata: Revocation list metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.job_id = job_id
        self.revocation_list_state = revocation_list_state
        self.registration_metadata = registration_metadata
        self.revocation_list_metadata = revocation_list_metadata

    @property
    def rev_reg_def_id(self):
        """Rev reg def id."""
        return self.revocation_list_state.revocation_list.rev_reg_def_id


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
    """GetRevListResult."""

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
        """Initialize an instance.

        Args:
            revocation_list: Revocation list
            resolution_metadata: Resolution metadata
            revocation_registry_metadata: Rev Reg metadata

        TODO: update this docstring - Anoncreds-break.

        """
        super().__init__(**kwargs)
        self.revocation_list = revocation_list
        self.resolution_metadata = resolution_metadata
        self.revocation_registry_metadata = revocation_registry_metadata


class GetRevListResultSchema(BaseModelSchema):
    """GetRevListResultSchema."""

    class Meta:
        """GetRevListResultSchema metadata."""

        model_class = GetRevListResult
        unknown = EXCLUDE

    revocation_list = fields.Nested(RevListSchema)
    resolution_metadata = fields.Str()
    revocation_registry_metadata = fields.Dict()
