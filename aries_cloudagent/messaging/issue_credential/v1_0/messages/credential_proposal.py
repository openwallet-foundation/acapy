"""A credential proposal content message."""

from marshmallow import fields

from ....agent_message import AgentMessage, AgentMessageSchema
from ..message_types import CREDENTIAL_PROPOSAL
from .inner.credential_preview import CredentialPreview, CredentialPreviewSchema


HANDLER_CLASS = (
    "aries_cloudagent.messaging.credentials.v1_0.handlers."
    + "credential_proposal_handler.CredentialProposalHandler"
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
        *,
        comment: str = None,
        credential_proposal: CredentialPreview = None,
        schema_id: str = None,
        cred_def_id: str = None,
        **kwargs
    ):
        """
        Initialize credential proposal object.

        Args:
            comment: optional human-readable comment
            credential_proposal: proposed credential preview
            schema_id: schema identifier
            cred_def_id: credential definition identifier
        """
        super(CredentialProposal, self).__init__(**kwargs)
        self.comment = comment
        self.credential_proposal = (
            credential_proposal if credential_proposal else CredentialPreview()
        )
        self.schema_id = schema_id
        self.cred_def_id = cred_def_id


class CredentialProposalSchema(AgentMessageSchema):
    """Credential proposal schema."""

    class Meta:
        """Credential proposal schema metadata."""

        model_class = CredentialProposal

    comment = fields.Str(required=False, allow_none=False)
    credential_proposal = fields.Nested(CredentialPreviewSchema, required=True)
    schema_id = fields.Str(required=False, allow_none=False)
    cred_def_id = fields.Str(required=False, allow_none=False)
