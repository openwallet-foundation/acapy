"""A credential proposal content message."""

from typing import Optional

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_DID_EXAMPLE,
    INDY_DID_VALIDATE,
    INDY_SCHEMA_ID_EXAMPLE,
    INDY_SCHEMA_ID_VALIDATE,
    MAJOR_MINOR_VERSION_EXAMPLE,
    MAJOR_MINOR_VERSION_VALIDATE,
)
from ..message_types import CREDENTIAL_PROPOSAL, PROTOCOL_PACKAGE
from .inner.credential_preview import CredentialPreview, CredentialPreviewSchema

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.credential_proposal_handler.CredentialProposalHandler"
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
        _id: Optional[str] = None,
        *,
        comment: Optional[str] = None,
        credential_proposal: Optional[CredentialPreview] = None,
        schema_id: Optional[str] = None,
        schema_issuer_did: Optional[str] = None,
        schema_name: Optional[str] = None,
        schema_version: Optional[str] = None,
        cred_def_id: Optional[str] = None,
        issuer_did: Optional[str] = None,
        **kwargs,
    ):
        """Initialize credential proposal object.

        Args:
            comment: optional human-readable comment
            credential_proposal: proposed credential preview
            schema_id: schema identifier
            schema_issuer_did: schema issuer DID
            schema_name: schema name
            schema_version: schema version
            cred_def_id: credential definition identifier
            issuer_did: credential issuer DID
            kwargs: additional key-value arguments to map into message class properties

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
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    credential_proposal = fields.Nested(
        CredentialPreviewSchema, required=False, allow_none=False
    )
    schema_id = fields.Str(
        required=False,
        allow_none=False,
        validate=INDY_SCHEMA_ID_VALIDATE,
        metadata={"example": INDY_SCHEMA_ID_EXAMPLE},
    )
    schema_issuer_did = fields.Str(
        required=False,
        allow_none=False,
        validate=INDY_DID_VALIDATE,
        metadata={"example": INDY_DID_EXAMPLE},
    )
    schema_name = fields.Str(required=False, allow_none=False)
    schema_version = fields.Str(
        required=False,
        allow_none=False,
        validate=MAJOR_MINOR_VERSION_VALIDATE,
        metadata={"example": MAJOR_MINOR_VERSION_EXAMPLE},
    )
    cred_def_id = fields.Str(
        required=False,
        allow_none=False,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={"example": INDY_CRED_DEF_ID_EXAMPLE},
    )
    issuer_did = fields.Str(
        required=False,
        allow_none=False,
        validate=INDY_DID_VALIDATE,
        metadata={"example": INDY_DID_EXAMPLE},
    )
