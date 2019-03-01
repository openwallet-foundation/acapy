"""Message type identifiers for Trust Pings."""

MESSAGE_FAMILY = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/trust_ping/1.0/"

PING = f"{MESSAGE_FAMILY}ping"
PING_RESPONSE = f"{MESSAGE_FAMILY}ping_response"

MESSAGE_TYPES = {
    PING: "indy_catalyst_agent.messaging.trustping." + "messages.ping.Ping",
    PING_RESPONSE: "indy_catalyst_agent.messaging.trustping."
    + "messages.ping_response.PingResponse",
}
