"""A credential proposal content message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
)

from ..message_types import CREDENTIAL_PROPOSAL, PROTOCOL_PACKAGE

from .inner.credential_preview import CredentialPreview, CredentialPreviewSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers."
    "credential_proposal_handler.CredentialProposalHandler"
)


class CredentialProposal(AgentMessage):
    """Class representing a credential proposal."""

    class Meta:
        """CredentialProposal metadata."""

        handler_class = HANDLER_CLASS
        schema_class = "CredentialProposalSchema"
        message_type = CREDENTIAL_PROPOSAL

    def __init__(
        self,
        _id: str = None,
        *,
        comment: str = None,
        credential_proposal: CredentialPreview = None,
        schema_id: str = None,
        schema_issuer_did: str = None,
        schema_name: str = None,
        schema_version: str = None,
        cred_def_id: str = None,
        issuer_did: str = None,
        **kwargs,
    ):
        """
        Initialize credential proposal object.

        Args:
            comment: optional human-readable comment
            credential_proposal: proposed credential preview
            schema_id: schema identifier
            schema_issuer_did: schema issuer DID
            schema_name: schema name
            schema_version: schema version
            cred_def_id: credential definition identifier
            issuer_did: credential issuer DID
        """
        super().__init__(_id, **kwargs)
        self.comment = comment
        self.credential_proposal = credential_proposal
        self.schema_id = schema_id
        self.schema_issuer_did = schema_issuer_did
        self.schema_name = schema_name
        self.schema_version = schema_version
        self.cred_def_id = cred_def_id
        self.issuer_did = issuer_did


class CredentialProposalSchema(AgentMessageSchema):
    """Credential proposal schema."""

    class Meta:
        """Credential proposal schema metadata."""

        model_class = CredentialProposal
        unknown = EXCLUDE

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    credential_proposal = fields.Nested(
        CredentialPreviewSchema, required=False, allow_none=False
    )
    schema_id = fields.Str(required=False, allow_none=False, **INDY_SCHEMA_ID)
    schema_issuer_did = fields.Str(required=False, allow_none=False, **INDY_DID)
    schema_name = fields.Str(required=False, allow_none=False)
    schema_version = fields.Str(required=False, allow_none=False, **INDY_VERSION)
    cred_def_id = fields.Str(required=False, allow_none=False, **INDY_CRED_DEF_ID)
    issuer_did = fields.Str(required=False, allow_none=False, **INDY_DID)
