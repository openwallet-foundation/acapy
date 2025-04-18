"""Multiledger related utility methods."""

import logging
from collections import OrderedDict

from ..config.settings import BaseSettings
from ..core.error import ProfileError

LOGGER = logging.getLogger(__name__)


def get_write_ledger_config_for_profile(settings: BaseSettings) -> dict:
    """Return initial/default write ledger config on profile creation."""
    write_ledger_config = None
    prod_write_ledger_pool = OrderedDict()
    non_prod_write_ledger_pool = OrderedDict()

    LOGGER.debug("Getting write ledger config for profile")
    for ledger_config in settings.get("ledger.ledger_config_list"):
        is_production = ledger_config.get("is_production")
        is_write = ledger_config.get("is_write")
        is_read_only = ledger_config.get("read_only")
        ledger_id = ledger_config.get("id") or ledger_config.get("pool_name")

        if is_production and (is_write or is_read_only):
            prod_write_ledger_pool[ledger_id] = ledger_config
        elif not is_production and (is_write or is_read_only):
            non_prod_write_ledger_pool[ledger_id] = ledger_config
        else:
            LOGGER.warning(
                "Ledger config %s is not a write ledger nor a read-only ledger",
                ledger_id,
            )

    write_ledger = settings.get("ledger.write_ledger")
    if write_ledger:
        if write_ledger in prod_write_ledger_pool:
            write_ledger_config = prod_write_ledger_pool.get(write_ledger)
        elif write_ledger in non_prod_write_ledger_pool:
            write_ledger_config = non_prod_write_ledger_pool.get(write_ledger)
        else:
            error_message = (
                "ledger.write_ledger in profile settings does not correspond to a "
                "write configurable ledger provided with --genesis-transactions-list"
            )
            LOGGER.error(error_message)
            raise ProfileError(error_message)
    else:
        if len(prod_write_ledger_pool) >= 1:
            LOGGER.debug("Using first production write ledger")
            write_ledger_config = (list(prod_write_ledger_pool.values()))[0]
        elif len(non_prod_write_ledger_pool) >= 1:
            LOGGER.debug("Using first non-production write ledger")
            write_ledger_config = (list(non_prod_write_ledger_pool.values()))[0]
        else:
            LOGGER.error("No write ledger configuration found in ledger_config_list")
            raise ProfileError(
                "No write ledger configuration found in ledger_config_list which "
                "was provided with --genesis-transactions-list"
            )

    return write_ledger_config
