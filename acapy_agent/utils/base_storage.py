"""Base storage utility for connection URI generation."""

import urllib


def get_postgres_connection_uri(storage_creds: dict, storage_config: dict) -> str:
    """Get the connection URI for the PostgreSQL database."""
    uri = "postgresql://"
    config_url = storage_config.get("url")
    if not config_url:
        raise ValueError("No 'url' provided for postgres store")
    if "account" not in storage_creds:
        raise ValueError("No 'account' provided for postgres store")
    if "password" not in storage_creds:
        raise ValueError("No 'password' provided for postgres store")
    account = urllib.parse.quote(storage_creds["account"])
    password = urllib.parse.quote(storage_creds["password"])
    # FIXME parse the URL, check for parameters, remove postgres:// prefix, etc
    # config url expected to be in the form "host:port"
    uri += f"{account}:{password}@{config_url}/postgres"
    return uri
