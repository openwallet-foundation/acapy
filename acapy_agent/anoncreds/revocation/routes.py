"""Shim to register events from acapy_agent.anoncreds.revocation.revocation_setup.

DefaultContextBuilder.load_plugins() specifies this package as an AnonCreds plugin,
allowing for this file to be picked up in PluginRegistry.register_protocol_events().
That automatically calls this register_events() function, and wires up the automated
revocation-registry management.
"""

from ...core.event_bus import EventBus
from .revocation_setup import DefaultRevocationSetup


def register_events(event_bus: EventBus) -> None:
    """Register events."""
    setup_manager = DefaultRevocationSetup()
    setup_manager.register_events(event_bus)
