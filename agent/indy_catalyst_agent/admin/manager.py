"""Admin API management classes."""


class AdminManager:
    """Admin manager class for letting back-end code send notifications."""

    @classmethod
    def add_notification(self, notify_type: str, notify_context: dict = None):
        """
        Add a new admin notification.

        Args:
            notify_type: The unique type identifier for the notification
            notify_context: An optional dictionary of additional parameters
        """
