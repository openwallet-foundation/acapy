"""Module that contains singleton classes for wallet operations."""


class IsAnonCredsSingleton:
    """Singleton class used as cache for anoncreds wallet-type queries."""

    instance = None
    wallets = set()

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def set_wallet(self, wallet: str):
        """Set a wallet name."""
        self.wallets.add(wallet)

    def remove_wallet(self, wallet: str):
        """Remove a wallet name."""
        self.wallets.discard(wallet)


class UpgradeInProgressSingleton:
    """Singleton class used as cache for upgrade in progress."""

    instance = None
    wallets = set()

    def __new__(cls, *args, **kwargs):
        """Create a new instance of the class."""
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def set_wallet(self, wallet: str):
        """Set a wallet name."""
        self.wallets.add(wallet)

    def remove_wallet(self, wallet: str):
        """Remove a wallet name."""
        self.wallets.discard(wallet)
