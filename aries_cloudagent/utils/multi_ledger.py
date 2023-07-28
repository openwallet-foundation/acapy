"""Multiledger related utility methods."""

from ..core.error import ProfileError
from ..config.settings import BaseSettings


def get_write_ledger_config_for_profile(settings: BaseSettings) -> dict:
    """Return initial/default write ledger config on profile creation."""
    write_ledger_config = None
    prod_write_ledger_pool = []
    non_prod_write_ledger_pool = []
    for ledger_config in settings.get("ledger.ledger_config_list"):
        if ledger_config.get("is_production") and ledger_config.get("is_write"):
            prod_write_ledger_pool.append(ledger_config)
        elif not ledger_config.get("is_production") and ledger_config.get("is_write"):
            non_prod_write_ledger_pool.append(ledger_config)
    if len(prod_write_ledger_pool) >= 1:
        write_ledger_config = prod_write_ledger_pool[0]
    elif len(non_prod_write_ledger_pool) >= 1:
        write_ledger_config = non_prod_write_ledger_pool[0]
    else:
        raise ProfileError(
            "No write ledger configuration found in ledger_config_list which "
            "was provided with --genesis-transactions-list"
        )
    return write_ledger_config
