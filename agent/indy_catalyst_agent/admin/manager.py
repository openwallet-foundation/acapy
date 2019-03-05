"""Admin API management classes."""


class AdminManager:
    """Admin manager class for letting back-end code send notifications."""

    SERVER = None

    @classmethod
    async def add_notification(cls, notify_type: str, notify_context: dict = None):
        """
        Add a new admin notification.

        Args:
            notify_type: The unique type identifier for the notification
            notify_context: An optional dictionary of additional parameters
        """

        if cls.SERVER:
            msg = {"type": notify_type, "context": notify_context or None}
            await cls.SERVER.add_notification(msg)
