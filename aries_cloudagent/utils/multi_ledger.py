"""Multiledger related utility methods."""
from collections import OrderedDict

from ..core.error import ProfileError
from ..config.settings import BaseSettings


def get_write_ledger_config_for_profile(settings: BaseSettings) -> dict:
    """Return initial/default write ledger config on profile creation."""
    write_ledger_config = None
    prod_write_ledger_pool = OrderedDict()
    non_prod_write_ledger_pool = OrderedDict()
    for ledger_config in settings.get("ledger.ledger_config_list"):
        if ledger_config.get("is_production") and ledger_config.get("is_write"):
            prod_write_ledger_pool[
                ledger_config.get("id") or ledger_config.get("pool_name")
            ] = ledger_config
        elif not ledger_config.get("is_production") and ledger_config.get("is_write"):
            non_prod_write_ledger_pool[
                ledger_config.get("id") or ledger_config.get("pool_name")
            ] = ledger_config
    if "ledger.write_ledger" in settings:
        if settings.get("ledger.write_ledger") in prod_write_ledger_pool:
            write_ledger_config = prod_write_ledger_pool.get(
                settings.get("ledger.write_ledger")
            )
        elif settings.get("ledger.write_ledger") in non_prod_write_ledger_pool:
            write_ledger_config = non_prod_write_ledger_pool.get(
                settings.get("ledger.write_ledger")
            )
        else:
            raise ProfileError(
                "The ledger.write_ledger in profile settings does not correspond to a"
                " write configurable ledger provided with --genesis-transactions-list"
            )
    else:
        if len(prod_write_ledger_pool) >= 1:
            write_ledger_config = (list(prod_write_ledger_pool.values()))[0]
        elif len(non_prod_write_ledger_pool) >= 1:
            write_ledger_config = (list(non_prod_write_ledger_pool.values()))[0]
        else:
            raise ProfileError(
                "No write ledger configuration found in ledger_config_list which "
                "was provided with --genesis-transactions-list"
            )
    return write_ledger_config
