"""Ledger Request Executor."""
from typing import Optional, Tuple

from ...config.base import InjectionError
from ...core.profile import Profile
from ...ledger.base import BaseLedger
from ...ledger.multiple_ledger.base_manager import (
    BaseMultipleLedgerManager,
    MultipleLedgerManagerError,
)

(
    GET_SCHEMA,
    GET_CRED_DEF,
    GET_REVOC_REG_DEF,
    GET_REVOC_REG_ENTRY,
    GET_KEY_FOR_DID,
    GET_ALL_ENDPOINTS_FOR_DID,
    GET_ENDPOINT_FOR_DID,
    GET_NYM_ROLE,
    GET_REVOC_REG_DELTA,
) = tuple(range(9))


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
        self, identifier: str, txn_record_type: int
    ) -> Tuple[Optional[str], Optional[BaseLedger]]:
        """Return ledger info given the record identifier."""
        # For seqNo
        if identifier.isdigit():
            return (None, self.profile.inject(BaseLedger))
        elif (
            self.profile.settings.get("ledger.ledger_config_list")
            and len(self.profile.settings.get("ledger.ledger_config_list")) > 0
        ):
            try:
                multiledger_mgr = self.profile.inject(BaseMultipleLedgerManager)
                extracted_did = multiledger_mgr.extract_did_from_identifier(identifier)
                if txn_record_type in tuple(range(4)):
                    cache_did = True
                else:
                    cache_did = False
                return await multiledger_mgr.lookup_did_in_configured_ledgers(
                    extracted_did, cache_did=cache_did
                )
            except (MultipleLedgerManagerError, InjectionError):
                pass
        return (None, self.profile.inject_or(BaseLedger))

    async def get_ledger_inst(self, ledger_id: str) -> Optional[BaseLedger]:
        """Return ledger instance from ledger_id set in config."""
        multiledger_mgr = self.profile.inject(BaseMultipleLedgerManager)
        return await multiledger_mgr.get_ledger_inst_by_id(ledger_id=ledger_id)
