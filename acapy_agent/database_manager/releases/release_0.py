"""Module docstring."""

from acapy_agent.database_manager.databases.postgresql_normalized.handlers import (
    generic_handler as postgres_generic_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.schema_context import (
    SchemaContext,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers import (
    generic_handler,
)

RELEASE = {
    "default": {
        "handlers": {
            "sqlite": lambda: generic_handler.GenericHandler(
                category="default", tags_table_name="items_tags"
            ),
            "postgresql": lambda: postgres_generic_handler.GenericHandler(
                category="default",
                tags_table_name="items_tags",
                schema_context=SchemaContext(),
            ),
        },
        "schemas": None,
    }
}
