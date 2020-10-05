"""Represents an Aries RFC 23 DID Exchange request message."""

from marshmallow import EXCLUDE, fields

from .....connections.models.diddoc import DIDDoc
from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import INDY_DID

from ..message_types import DIDEX_REQUEST, PROTOCOL_PACKAGE

HANDLER_CLASS = f"{PROTOCOL_PACKAGE}.handlers.request_handler.DIDExRequestHandler"


class DIDExRequest(AgentMessage):
    """Represents a DID Exchange request."""

    class Meta:
        handler_class =
        message_type = DIDEX_REQUEST
        schema_class = "DIDExRequestSchema"

    def __init(
        self,
        label: str = None,
        did: str = None,
        did_doc_attach = None,
        **kwargs,
    ):
        """
        Initialize DID exchange request object.

        Args:
            csffdslff
        """
        super().__init__(**kwargs)
        self.label = label
        self.did = did
        self.did_doc_attach = did_doc_attach


class DIDExRequestSchema(AgentMessageSchema):
    """DID Exchange request schema class."""

    class Meta:
        model_class = DIDExRequest
        unknown = EXCLUDE

    did = fields.Str(description="DID of exchange", **INDY_DID)
    did_doc_attach = fields.Nested(
        AttachDecoratorDataSchema,
        required=False,
        description="DID Doc associated with DID as signed attachment",
        data_key="did_doc~attach",
    )
