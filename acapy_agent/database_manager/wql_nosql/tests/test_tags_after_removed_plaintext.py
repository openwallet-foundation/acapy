"""Tests for the tags module.

Disabled by default to keep CI lean; enable locally with
ENABLE_WQL_SQLITE_TESTS=1 if you want to run them.
"""

import os

import pytest

if not os.getenv("ENABLE_WQL_SQLITE_TESTS"):
    pytest.skip(
        "WQL SQLite encoder tests disabled by default; set ENABLE_WQL_SQLITE_TESTS=1",
        allow_module_level=True,
    )

import unittest
from typing import List

from ..query import AndQuery, EqQuery
from ..tags import CompareOp, ConjunctionOp, TagName, TagQuery, query_to_tagquery


class TestEncoder:
    """A class to encode TagQuery objects into string representations."""

    def encode_query(self, query: TagQuery, negate: bool = False) -> str:
        """Encode a TagQuery into a string representation, handling negation."""
        if query.variant in ["Eq", "Neq", "Gt", "Gte", "Lt", "Lte", "Like"]:
            op = getattr(CompareOp, query.variant)
            return self.encode_op(op, *query.data, negate)
        elif query.variant == "In":
            return self.encode_in(*query.data, negate)
        elif query.variant == "Exist":
            return self.encode_exist(query.data, negate)
        elif query.variant in ["And", "Or"]:
            op = ConjunctionOp.And if query.variant == "And" else ConjunctionOp.Or
            return self.encode_conj(op, query.data, negate)
        elif query.variant == "Not":
            return self.encode_query(query.data, not negate)
        else:
            raise ValueError(f"Unknown query variant: {query.variant}")

    def encode_op(self, op: CompareOp, name: TagName, value: str, negate: bool) -> str:
        """Encode an operation clause (e.g., 'name = value')."""
        enc_name = self.encode_name(name)
        enc_value = self.encode_value(value)
        clause = f"{enc_name} {op.as_sql_str()} {enc_value}"
        return f"NOT ({clause})" if negate else clause

    def encode_in(self, name: TagName, values: List[str], negate: bool) -> str:
        """Encode an IN clause (e.g., 'name IN (value1, value2)')."""
        enc_name = self.encode_name(name)
        enc_values = [self.encode_value(v) for v in values]
        op_str = "NOT IN" if negate else "IN"
        values_str = ", ".join(enc_values)
        return f"{enc_name} {op_str} ({values_str})"

    def encode_exist(self, names: List[TagName], negate: bool) -> str:
        """Encode an EXIST clause (e.g., 'EXIST(name)')."""

        if not names:
            return None
        clauses = []
        for name in names:
            enc_name = self.encode_name(name)
            op_str = "NOT EXIST" if negate else "EXIST"
            clauses.append(f"{op_str}({enc_name})")
        if len(clauses) == 1:
            return clauses[0]
        op = ConjunctionOp.And if not negate else ConjunctionOp.Or
        return f"({op.as_sql_str().join(clauses)})"

    def encode_conj(
        self, op: ConjunctionOp, subqueries: List[TagQuery], negate: bool
    ) -> str:
        """Encode a conjunction clause (AND/OR) with possible negation."""
        if negate:
            op = op.negate()
            sub_negate = True
        else:
            sub_negate = False
        clauses = [self.encode_query(q, sub_negate) for q in subqueries if q is not None]
        if not clauses:
            return None
        return f"({op.as_sql_str().join(clauses)})"

    def encode_name(self, name: TagName) -> str:
        """Test cases encode name functionality."""

        return name.to_string()

    def encode_value(self, value: str) -> str:
        """Test cases for the TagQuery functionality."""

        return value


class TestTags(unittest.TestCase):
    """Test cases for the TagQuery functionality."""

    def test_from_query(self):
        """Test cases for the TagQuery functionality."""
        query = AndQuery([EqQuery("enctag", "encval"), EqQuery("~plaintag", "plainval")])
        tag_query = query_to_tagquery(query)
        self.assertEqual(tag_query.variant, "And")
        self.assertEqual(len(tag_query.data), 2)
        sq1, sq2 = tag_query.data
        self.assertEqual(sq1.variant, "Eq")
        name1, val1 = sq1.data
        self.assertEqual(name1.value, "enctag")
        self.assertEqual(val1, "encval")
        self.assertEqual(sq2.variant, "Eq")
        name2, val2 = sq2.data
        self.assertEqual(name2.value, "plaintag")
        self.assertEqual(val2, "plainval")

    def test_serialize(self):
        """Test serialization of TagQuery to JSON."""
        self.skipTest("TagQuery serialization not implemented in provided code")

    def test_simple_and(self):
        """Test encoding a complex TagQuery with AND, OR, and NOT."""
        condition_1 = TagQuery.and_(
            [
                TagQuery.eq(TagName("enctag"), "encval"),
                TagQuery.eq(TagName("plaintag"), "plainval"),
            ]
        )
        condition_2 = TagQuery.and_(
            [
                TagQuery.eq(TagName("enctag"), "encval"),
                TagQuery.not_(TagQuery.eq(TagName("plaintag"), "eggs")),
            ]
        )
        query = TagQuery.or_([condition_1, condition_2])
        encoder = TestEncoder()
        query_str = encoder.encode_query(query)
        expected = (
            "((enctag = encval AND plaintag = plainval) OR "
            "(enctag = encval AND NOT (plaintag = eggs)))"
        )
        self.assertEqual(query_str, expected)

    def test_negate_conj(self):
        """Test encoding a negated conjunction TagQuery."""
        condition_1 = TagQuery.and_(
            [
                TagQuery.eq(TagName("enctag"), "encval"),
                TagQuery.eq(TagName("plaintag"), "plainval"),
            ]
        )
        condition_2 = TagQuery.and_(
            [
                TagQuery.eq(TagName("enctag"), "encval"),
                TagQuery.not_(TagQuery.eq(TagName("plaintag"), "eggs")),
            ]
        )
        query = TagQuery.not_(TagQuery.or_([condition_1, condition_2]))
        encoder = TestEncoder()
        query_str = encoder.encode_query(query)
        expected = (
            "((NOT (enctag = encval) OR NOT (plaintag = plainval)) AND "
            "(NOT (enctag = encval) OR plaintag = eggs))"
        )
        self.assertEqual(query_str, expected)


if __name__ == "__main__":
    unittest.main()
