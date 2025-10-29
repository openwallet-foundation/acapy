"""Module docstring."""

import re
from typing import Optional


class SchemaContext:
    """Context for managing database schema configurations."""

    DEFAULT_SCHEMA_NAME = "postgres"

    def __init__(self, schema_name: Optional[str] = None):
        """Initialize schema context."""
        self.schema_name = self._validate_schema_name(
            schema_name or self.DEFAULT_SCHEMA_NAME
        )

    def _validate_schema_name(self, schema_name: str) -> str:
        if not re.match(r"^\w+$", schema_name, re.ASCII):
            raise ValueError(
                f"Invalid schema name '{schema_name}': must contain only "
                f"alphanumeric characters and underscores"
            )
        return schema_name

    def qualify_table(self, table_name: str) -> str:
        """Qualify table name with schema prefix."""
        # just retrun fully qualified table name with the schema prefix.
        return f"{self.schema_name}.{table_name}"

    def __str__(self) -> str:
        """Return string representation of schema context."""
        return self.schema_name
