
"""Message type identifiers for Transactions."""

from ...didcomm_prefix import DIDCommPrefix

# Message types

TRANSACTION_REQUEST = f"transactions/1.0/request"
ENDORSED_TRANSACTION_RESPONSE = f"transactions/1.0/endorse"
REFUSED_TRANSACTION_RESPONSE = f"transactions/1.0/refuse"
CANCEL_TRANSACTION = f"transactions/1.0/cancel"
TRANSACTION_RESEND = f"transactions/1.0/resend"
ATTACHED_MESSAGE = f"transactions/1.0/message"
PROTOCOL_PACKAGE = "aries_cloudagent.protocols.endorse_transaction.v1_0"


MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        TRANSACTION_REQUEST: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_request.TransactionRequest"
        ),
        ENDORSED_TRANSACTION_RESPONSE: (
            f"{PROTOCOL_PACKAGE}.messages.endorsed_transaction_response.EndorsedTransactionResponse"
        ),
        REFUSED_TRANSACTION_RESPONSE:(
            f"{PROTOCOL_PACKAGE}.messages.refused_transaction_response.RefusedTransactionResponse"
        ),
        CANCEL_TRANSACTION: (
            f"{PROTOCOL_PACKAGE}.messages.cancel_transaction.CancelTransaction"
        ),
        TRANSACTION_RESEND: (
            f"{PROTOCOL_PACKAGE}.messages.transaction_resend.TransactionResend"
        )
    }
)
