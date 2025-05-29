"""Message type identifiers for problem reports."""

from ...didcomm_prefix import DIDCommPrefix

SPEC_URI = (
    "https://github.com/decentralized-identity/aries-rfcs/tree/"
    "437d80d752d667ee00b1b6446892980ebda86da3/features/0035-report-problem"
)

# Message types
PROBLEM_REPORT = "notification/1.0/problem-report"

PROTOCOL_PACKAGE = "acapy_agent.protocols.problem_report.v1_0"

MESSAGE_TYPES = DIDCommPrefix.qualify_all(
    {PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.message.ProblemReport"}
)
