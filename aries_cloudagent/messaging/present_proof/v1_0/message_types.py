"""Message and inner object type identifiers for Connections."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/present-proof/1.0/"

# Message types

PRESENTATION_PROPOSAL = f"{MESSAGE_FAMILY}propose-presentation"
PRESENTATION_REQUEST = f"{MESSAGE_FAMILY}request-presentation"
PRESENTATION = f"{MESSAGE_FAMILY}presentation"

TOP = "aries_cloudagent.messaging.present_proof.v1_0"
MESSAGE_TYPES = {
    PRESENTATION_PROPOSAL: f"{TOP}.messages.presentation_proposal.PresentationProposal",
    PRESENTATION_REQUEST: f"{TOP}.messages.presentation_request.PresentationRequest",
    PRESENTATION: f"{TOP}.messages.presentation.Presentation"
}

# Inner object types
PRESENTATION_PREVIEW = f"{MESSAGE_FAMILY}presentation-preview"
