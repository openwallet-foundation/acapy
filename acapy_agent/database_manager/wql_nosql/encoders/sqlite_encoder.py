"""Module docstring."""

from typing import List

from ..tags import CompareOp, ConjunctionOp, TagName, TagQueryEncoder


class SqliteTagEncoder(TagQueryEncoder):
    """Encoder for generating SQLite-compatible SQL queries from TagQuery objects.

    Uses '?' placeholders for parameters.
    """

    def __init__(self, enc_name, enc_value):
        """Initialize the encoder with functions to encode tag names and values.

        Args:
            enc_name (callable): Function to encode tag names (str -> bytes).
            enc_value (callable): Function to encode tag values (str -> bytes).

        """
        self.enc_name = enc_name
        self.enc_value = enc_value
        self.arguments = []  # List to store parameter values

    def encode_name(self, name: TagName) -> bytes:
        """Encode the tag name using the provided enc_name function."""
        return self.enc_name(name.value)

    def encode_value(self, value: str) -> bytes:
        """Encode the tag value using the provided enc_value function."""
        return self.enc_value(value)

    def encode_op_clause(
        self, op: CompareOp, enc_name: bytes, enc_value: bytes, negate: bool
    ) -> str:
        """Encode a comparison operation clause for SQLite.

        Args:
            op (CompareOp): The comparison operator.
            enc_name (bytes): Encoded tag name.
            enc_value (bytes): Encoded tag value.
            negate (bool): Whether to negate the clause.

        Returns:
            str: SQL clause string.

        """
        self.arguments.append(enc_name)
        self.arguments.append(enc_value)
        query = (
            f"i.id {'NOT IN' if negate else 'IN'} (SELECT item_id FROM items_tags "
            f"WHERE name = ? AND value {op.as_sql_str()} ?)"
        )
        return query

    def encode_in_clause(
        self, enc_name: bytes, enc_values: List[bytes], negate: bool
    ) -> str:
        """Encode an 'IN' clause for multiple values in SQLite.

        Args:
            enc_name (bytes): Encoded tag name.
            enc_values (List[bytes]): List of encoded tag values.
            negate (bool): Whether to use 'NOT IN' instead of 'IN'.

        Returns:
            str: SQL clause string.

        """
        self.arguments.append(enc_name)
        self.arguments.extend(enc_values)
        name_placeholder = "?"
        value_placeholders = ", ".join(["?" for _ in enc_values])
        query = (
            f"i.id {'NOT IN' if negate else 'IN'} (SELECT item_id FROM items_tags "
            f"WHERE name = {name_placeholder} AND value IN ({value_placeholders}))"
        )
        return query

    def encode_exist_clause(self, enc_name: bytes, negate: bool) -> str:
        """Encode an 'EXISTS' clause for tag existence in SQLite.

        Args:
            enc_name (bytes): Encoded tag name.
            negate (bool): Whether to negate the existence check.

        Returns:
            str: SQL clause string.

        """
        self.arguments.append(enc_name)
        query = (
            f"i.id {'NOT IN' if negate else 'IN'} (SELECT item_id FROM items_tags "
            f"WHERE name = ?)"
        )
        return query

    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        """Encode a conjunction clause (AND/OR) for SQLite.

        Args:
            op (ConjunctionOp): The conjunction operator.
            clauses (List[str]): List of SQL clause strings to combine.

        Returns:
            str: Combined SQL clause string.

        """
        if not clauses:
            # For empty OR, return a clause that evaluates to false
            if op == ConjunctionOp.Or:
                return "0"
            # For empty AND, return a clause that evaluates to true
            return "1"
        return "(" + op.as_sql_str().join(clauses) + ")"
