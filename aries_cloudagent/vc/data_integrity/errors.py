"""Problem Details objects for error handling."""

# https://www.w3.org/TR/vc-data-integrity/#processing-errors
PROBLEM_DETAILS = {
    "PROOF_GENERATION_ERROR": {
        "type": "https://w3id.org/security#PROOF_GENERATION_ERROR"
    },
    "PROOF_VERIFICATION_ERROR": {
        "type": "https://w3id.org/security#PROOF_VERIFICATION_ERROR"
    },
    "PROOF_TRANSFORMATION_ERROR": {
        "type": "https://w3id.org/security#PROOF_TRANSFORMATION_ERROR"
    },
    "INVALID_DOMAIN_ERROR": {"type": "https://w3id.org/security#INVALID_DOMAIN_ERROR"},
    "INVALID_CHALLENGE_ERROR": {
        "type": "https://w3id.org/security#INVALID_CHALLENGE_ERROR"
    },
}
