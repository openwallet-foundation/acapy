"""Represents a transaction request message."""

from marshmallow import EXCLUDE, fields

from .....messaging.agent_message import AgentMessage, AgentMessageSchema
from .....messaging.valid import UUID4_EXAMPLE
from ..message_types import PROTOCOL_PACKAGE, TRANSACTION_REQUEST

HANDLER_CLASS = (
    f"{PROTOCOL_PACKAGE}.handlers.transaction_request_handler.TransactionRequestHandler"
)


class TransactionRequest(AgentMessage):
    """Class representing a transaction request message."""

    class Meta:
        """Metadata for a transaction request message."""

        handler_class = HANDLER_CLASS
        message_type = TRANSACTION_REQUEST
        schema_class = "TransactionRequestSchema"

    def __init__(
        self,
        *,
        transaction_id: str = None,
        signature_request: dict = None,
        timing: dict = None,
        transaction_type: str = None,
        messages_attach: dict = None,
        endorser_write_txn: bool = None,
        **kwargs,
    ):
        """
        Initialize the transaction request object.

        Args:
            transaction_id: The transaction id of the transaction record
            signature_request: The signature that is requested
            timing: The time till the endorser should endorse/refuse a transaction
            transaction_type: The type of transaction
            messages_attach: The attached message describing the actual transaction
        """
        super().__init__(**kwargs)
        self.transaction_id = transaction_id
        self.signature_request = signature_request
        self.timing = timing
        self.transaction_type = transaction_type
        self.messages_attach = messages_attach
        self.endorser_write_txn = endorser_write_txn


class TransactionRequestSchema(AgentMessageSchema):
    """Transaction request schema class."""

    class Meta:
        """Transaction request schema metadata."""

        model_class = TransactionRequest
        unknown = EXCLUDE

    transaction_id = fields.Str(required=False, metadata={"example": UUID4_EXAMPLE})
    signature_request = fields.Dict(
        required=False,
        metadata={
            "example": {
                "context": "did:sov",
                "method": "add-signature",
                "signature_type": "<requested signature type>",
                "signer_goal_code": "transaction.endorse",
                "author_goal_code": "transaction.ledger.write",
            }
        },
    )
    timing = fields.Dict(
        required=False, metadata={"example": {"expires_time": "1597708800"}}
    )
    transaction_type = fields.Str(required=False, metadata={"example": "101"})
    messages_attach = fields.Dict(
        required=False,
        metadata={
            "example": {
                "@id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
                "mime-type": "application/json",
                "data": {
                    "json": {
                        "endorser": "V4SGRU86Z58d6TV7PBUe6f",
                        "identifier": "LjgpST2rjsoxYegQDRm7EL",
                        "operation": {
                            "data": {
                                "attr_names": ["first_name", "last_name"],
                                "name": "test_schema",
                                "version": "2.1",
                            },
                            "type": "101",
                        },
                        "protocolVersion": 2,
                        "reqId": 1597766666168851000,
                        "signatures": {
                            "LjgpST2rjsox": (
                                "4uq1mUATKMn6Y9sTaGWyuPgjUEw5UBysWNbfSqCfnbm1Vnfw"
                            )
                        },
                        "taaAcceptance": {
                            "mechanism": "manual",
                            "taaDigest": (
                                "f50feca75664270842bd4202c2d6f23e4c6a7e0fc2feb9f62"
                            ),
                            "time": 1597708800,
                        },
                    }
                },
            }
        },
    )
    endorser_write_txn = fields.Boolean(
        required=False,
        metadata={
            "description": (
                "If True, Endorser will write the transaction after endorsing it"
            ),
            "example": True,
        },
    )
