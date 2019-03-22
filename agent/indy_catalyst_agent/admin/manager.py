"""Admin API management classes."""


from .base_server import BaseAdminServer


class AdminManager:
    """Admin manager class for letting back-end code send event notifications."""

    SERVER = None

    @classmethod
    def get_server(cls) -> BaseAdminServer:
        """Set the global server instance."""
        return cls.SERVER

    @classmethod
    def set_server(cls, server: BaseAdminServer):
        """Set the global server instance."""
        cls.SERVER = server

    @classmethod
    async def add_event(cls, event_type: str, event_context: dict = None):
        """
        Add a new admin event.

        Args:
            event_type: The unique type identifier for the event
            event_context: An optional dictionary of additional parameters
        """

        if cls.SERVER:
            msg = {"type": event_type, "context": event_context or None}
            await cls.SERVER.add_event(msg)
