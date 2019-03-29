import logging
import os

LOGGER = logging.getLogger(__name__)


def indy_general_wallet_config():
    # wallet configuration
    # - your choice of postgres or sqlite at the moment
    # - defaults to sqlite for compatibility
    wallet_type = os.environ.get('WALLET_TYPE')
    wallet_type = wallet_type.lower() if wallet_type else 'sqlite'

    wallet_encryp_key = os.environ.get('WALLET_ENCRYPTION_KEY') or "key"

    ret = {"type": wallet_type}

    if wallet_type == 'postgres_storage':
        LOGGER.info("Using Postgres storage ...")

        # postgresql wallet-db configuration
        wallet_host = os.environ.get('POSTGRESQL_WALLET_HOST')
        if not wallet_host:
            raise ValueError('POSTGRESQL_WALLET_HOST must be set.')
        wallet_port = os.environ.get('POSTGRESQL_WALLET_PORT')
        if not wallet_port:
            raise ValueError('POSTGRESQL_WALLET_PORT must be set.')
        wallet_user = os.environ.get('POSTGRESQL_WALLET_USER')
        if not wallet_user:
            raise ValueError('POSTGRESQL_WALLET_USER must be set.')
        wallet_password = os.environ.get('POSTGRESQL_WALLET_PASSWORD')
        if not wallet_password:
            raise ValueError('POSTGRESQL_WALLET_PASSWORD must be set.')
        wallet_admin_user = 'postgres'
        wallet_admin_password = os.environ.get('POSTGRESQL_WALLET_ADMIN_PASSWORD')

        # TODO pass in as env parameter - key for encrypting the wallet contents

        ret["params"] = {
            "storage_config": {"url": "{}:{}".format(wallet_host, wallet_port)},
        }
        stg_creds = {"account": wallet_user, "password": wallet_password}
        if wallet_admin_password:
            stg_creds["admin_account"] = wallet_admin_user
            stg_creds["admin_password"] = wallet_admin_password
        ret["access_creds"] = {
            "key": wallet_encryp_key,
            "storage_credentials": stg_creds,
            "key_derivation_method": "ARGON2I_MOD",
        }

    elif wallet_type == 'sqlite':
        LOGGER.info("Using Sqlite storage ...")
        ret["access_creds"] = {"key": wallet_encryp_key}
    else:
        raise ValueError('Unknown WALLET_TYPE: {}'.format(wallet_type))

    return ret


def indy_wallet_config(wallet_cfg: dict):
    wallet_seed = os.environ.get('INDY_WALLET_SEED')
    if not wallet_seed:
        raise ValueError('INDY_WALLET_SEED must be set')

    if wallet_cfg['type'] == 'postgres_storage':
        return {
            "name": "tob_holder",
            "seed": wallet_seed,
            "type": "postgres_storage",
            "params": wallet_cfg["params"],
            "access_creds": wallet_cfg["access_creds"],
        }
    return {
        "name": "TheOrgBook_Holder_Wallet",
        "seed": wallet_seed,
        "access_creds": wallet_cfg["access_creds"],
    }
