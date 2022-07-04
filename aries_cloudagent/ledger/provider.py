from aries_cloudagent.ledger.base import BaseLedger
from aries_cloudagent.ledger.centralized import CentralizedSdkLedger
from aries_cloudagent.ledger.indy import IndySdkLedger
from aries_cloudagent.ledger.indy_vdr import IndyVdrLedger


class LedgerProvider:
    """
    Init a ledger provider class which is able to retrieve the correct ledger class
    according to the specified settings.
    """

    WALLET_SUPPORTED_LEDGERS = {
        "askar": {
            IndyVdrLedger.BACKEND_NAME: IndyVdrLedger
        },
        "indy": {
            IndySdkLedger.BACKEND_NAME: IndySdkLedger,
            CentralizedSdkLedger.BACKEND_NAME: CentralizedSdkLedger
        },
    }

    def __init__(self, settings):
        """Create a new ledger provider."""

        self.wallet_type = settings["wallet.type"]
        self.wallet_ledger = settings["wallet.ledger"]

    def get_ledger(self):
        """Retrieve the correct ledger."""

        if self.wallet_type in self.WALLET_SUPPORTED_LEDGERS:
            supported_ledgers = self.WALLET_SUPPORTED_LEDGERS.get(self.wallet_type)
            if self.wallet_ledger not in supported_ledgers:
                raise UnsupportedLedgerException(self.wallet_type, self.wallet_ledger)
            return supported_ledgers.get(self.wallet_ledger)

    def add_supported_ledger_for_wallet(self, wallet_type: str, ledger: BaseLedger):
        """Add ledger support for a wallet."""

        self.WALLET_SUPPORTED_LEDGERS[wallet_type] = ledger


class UnsupportedLedgerException(Exception):
    """Raised when the specifiec ledger is not supported by the specified wallet type"""

    def __init__(self, wallet_type, ledger):
        """Create a new NoSuppoertedLedgerException"""

        super().__init__(f"Unsupported ledger \"{ledger}\" for wallet of type \"{wallet_type}\".")
