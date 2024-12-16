"""Handler for the trust ping protocol."""

from acapy_agent.transport.inbound.message import InboundMessage


async def handle_trust_ping(message: InboundMessage):
    """."""
    return False
