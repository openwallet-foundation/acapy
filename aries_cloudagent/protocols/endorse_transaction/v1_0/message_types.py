"""Message type identifiers for Connections."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "9b0aaa39df7e8bd434126c4b33c097aae78d65bf/features/0160-connection-protocol"
)

# Message types

TRANSACTION_REQUEST = f"transactions/1.0/request"
TRANSACTION_RESPONSE = f"transactions/1.0/response"
CANCEL_TRANSACTION = f"transactions/1.0/cancel"
TRANSACTION_RESEND = f"transactions/1.0/resend"
PROTOCOL_PACKAGE = "aries_cloudagent.protocols.endorse_transaction.v1_0"


MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        TRANSACTION_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_request.TransactionRequest"
        ),
        TRANSACTION_RESPONSE: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_response.TransactionResponse"
        ),
        CANCEL_TRANSACTION: (
            f"{PROTOCOL_PACKAGE}.messages.cancel_transaction.CancelTransaction"
        ),
        TRANSACTION_RESEND: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_resend.TransactionResend"
        )
    }
)
