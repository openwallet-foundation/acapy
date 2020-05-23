"""Message type identifiers for problem reports."""

SPEC_URI = (
    "https://github.com/hyperledger/aries-rfcs/tree/"
    "89d14c15ab35b667e7a9d04fe42d4d48b10468cf/features/0035-report-problem"
)
PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/notification/1.0"

PROBLEM_REPORT = f"{PROTOCOL_URI}/problem-report"

NEW_PROTOCOL_URI = "https://didcomm.org/notification/1.0"

NEW_PROBLEM_REPORT = f"{NEW_PROTOCOL_URI}/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.problem_report.v1_0"

MESSAGE_TYPES = {
    PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.message.ProblemReport",
    NEW_PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.message.ProblemReport",
}
