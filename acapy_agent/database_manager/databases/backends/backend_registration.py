# from ...dbstore import register_backend
# from ...databases.sqlite_normalized.backend import SqliteBackend
# from ...databases.postgresql_normalized.backend import PostgresqlBackend

# def register_backends():
#     register_backend("sqlite", SqliteBackend())
#     register_backend("postgresql", PostgresqlBackend())

import logging
from ...dbstore import register_backend
from ...databases.sqlite_normalized.backend import SqliteBackend
from ...databases.postgresql_normalized.backend import PostgresqlBackend

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

def register_backends():
    """Register database backends for SQLite and PostgreSQL."""
    LOGGER.debug("Registering backends")
    register_backend("sqlite", SqliteBackend())
    LOGGER.debug("Registered backend: sqlite")
    register_backend("postgres", PostgresqlBackend())
    LOGGER.debug("Registered backend: postgres")