"""Message type identifiers for problem reports."""

PROTOCOL_URI = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/notification/1.0"

PROBLEM_REPORT = f"{PROTOCOL_URI}/problem-report"

NEW_PROTOCOL_URI = "https://didcomm.org/notification/1.0"

NEW_PROBLEM_REPORT = f"{NEW_PROTOCOL_URI}/problem-report"

PROTOCOL_PACKAGE = "aries_cloudagent.protocols.problem_report"

MESSAGE_TYPES = {
    PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.message.ProblemReport",
    NEW_PROBLEM_REPORT: f"{PROTOCOL_PACKAGE}.message.ProblemReport"
}
