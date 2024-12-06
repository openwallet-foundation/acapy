"""Message type identifiers for Trust Pings."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = "https://github.com/hyperledger/aries-rfcs/tree/main/features/0794-did-rotate"

# Message types
ROTATE = "did-rotate/1.0/rotate"
ACK = "did-rotate/1.0/ack"
HANGUP = "did-rotate/1.0/hangup"
PROBLEM_REPORT = "did-rotate/1.0/problem-report"

PROTOCOL_PACKAGE = "acapy_agent.protocols.did_rotate.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {
        ROTATE: f"{PROTOCOL_PACKAGE}.messages.rotate.Rotate",
        ACK: f"{PROTOCOL_PACKAGE}.messages.ack.RotateAck",
        HANGUP: f"{PROTOCOL_PACKAGE}.messages.hangup.Hangup",
        PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.messages.problem_report.RotateProblemReport",
    }
)
