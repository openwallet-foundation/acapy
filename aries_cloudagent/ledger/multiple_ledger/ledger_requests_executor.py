"""Ledger Request Executor."""
from typing import Tuple, Union, Optional

from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...ledger.indy import IndySdkLedger
from ...ledger.indy_vdr import IndyVdrLedger
from ...ledger.multiple_ledger.base_manager import (
    BaseMultipleLedgerManager,
    MultipleLedgerManagerError,
)


class IndyLedgerRequestsExecutor:
    """Executes Ledger Requests based on multiple ledger config, if set."""

    def __init__(
        self,
        profile: Profile,
    ):
        """Initialize IndyLedgerRequestsExecutor.

        Args:
            profile: The active profile instance

        """
        self.profile = profile

    async def get_ledger_for_identifier(
        self, identifier: str
    ) -> Union[
        Optional[IndyVdrLedger],
        Optional[IndySdkLedger],
        Tuple[str, IndyVdrLedger],
        Tuple[str, IndySdkLedger],
    ]:
        """Return ledger info given the record identifier."""
        if (
            self.profile.settings.get("ledger.ledger_config_list")
            and len(self.profile.settings.get("ledger.ledger_config_list")) > 0
        ):
            try:
                multiledger_mgr = self.profile.inject(BaseMultipleLedgerManager)
                extracted_did = multiledger_mgr.extract_did_from_identifier(identifier)
                return await multiledger_mgr.lookup_did_in_configured_ledgers(
                    extracted_did
                )
            except MultipleLedgerManagerError:
                return self.profile.inject(BaseLedger)
        else:
            return self.profile.inject(BaseLedger)
