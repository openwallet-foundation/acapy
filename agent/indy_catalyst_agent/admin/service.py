"""Admin API service classes."""

from .base_server import BaseAdminServer


class AdminService:
    """Admin service handler for letting back-end code send event notifications."""

    def __init__(self, server: BaseAdminServer):
        """Init admin service."""
        self._server = server

    async def add_event(self, event_type: str, event_context: dict = None):
        """
        Add a new admin event.

        Args:
            event_type: The unique type identifier for the event
            event_context: An optional dictionary of additional parameters
        """

        if self._server:
            msg = {"type": event_type, "context": event_context or None}
            await self._server.add_event(msg)
