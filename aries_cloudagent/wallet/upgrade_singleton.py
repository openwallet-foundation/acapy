"""Singleton class to ensure that upgrade is isolated."""


class UpgradeSingleton:
    """Singleton class to ensure that upgrade is isolated."""

    instance = None
    current_upgrades = set()

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def set_wallet(self, wallet: str):
        """Set a wallet name."""
        self.current_upgrades.add(wallet)

    def remove_wallet(self, wallet: str):
        """Remove a wallet name."""
        self.current_upgrades.discard(wallet)
