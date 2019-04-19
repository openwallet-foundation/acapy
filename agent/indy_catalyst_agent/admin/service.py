"""Admin API service classes."""

from .base_server import BaseAdminServer
from ..messaging.base_context import BaseRequestContext
from ..service.base import BaseService


class AdminService(BaseService):
    """Admin service handler for letting back-end code send event notifications."""

    def __init__(self, context: BaseRequestContext, server: BaseAdminServer):
        """Init admin service."""
        self._context = context
        self._server = server

    @classmethod
    def service_handler(cls, server: BaseAdminServer):
        """Quick accessor for conductor to use."""

        async def get_instance(context: BaseRequestContext):
            """Return registered server."""
            return AdminService(context, server)

        return get_instance

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
