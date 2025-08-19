import re
from typing import Optional


class SchemaContext:
    DEFAULT_SCHEMA_NAME = "myuser"

    def __init__(self, schema_name: Optional[str] = None):
        self.schema_name = self._validate_schema_name(
            schema_name or self.DEFAULT_SCHEMA_NAME
        )

    def _validate_schema_name(self, schema_name: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", schema_name):
            raise ValueError(
                f"Invalid schema name '{schema_name}': must contain only alphanumeric characters and underscores"
            )
        return schema_name

    def qualify_table(self, table_name: str) -> str:
        # just retrun fully qualified table name with the schema prefix.
        return f"{self.schema_name}.{table_name}"

    def __str__(self) -> str:
        return self.schema_name
