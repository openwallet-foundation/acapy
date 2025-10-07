"""Database backend registration module."""

import logging

from ...dbstore import register_backend

LOGGER = logging.getLogger(__name__)


def register_backends():
    """Register database backends for SQLite and PostgreSQL."""
    LOGGER.debug("Registering database backends")

    # Register SQLite backend
    try:
        from ...databases.sqlite_normalized.backend import SqliteBackend

        sqlite_backend = SqliteBackend()
        register_backend("sqlite", sqlite_backend)
        LOGGER.debug("Registered backend: sqlite")
    except ImportError as e:
        LOGGER.warning(f"Could not register SQLite backend: {e}")

    # Register PostgreSQL backend (both postgres and postgresql prefixes)
    try:
        from ...databases.postgresql_normalized.backend import PostgresqlBackend

        postgresql_backend = PostgresqlBackend()
        register_backend("postgres", postgresql_backend)
        register_backend("postgresql", postgresql_backend)
        LOGGER.debug("Registered backends: postgres, postgresql")
    except ImportError as e:
        LOGGER.warning(f"Could not register PostgreSQL backend: {e}")
