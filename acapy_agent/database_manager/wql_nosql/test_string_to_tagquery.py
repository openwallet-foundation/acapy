"""Tests for string to TagQuery conversion."""

import random
import string
import unittest

from .query import (
    AndQuery,
    EqQuery,
    ExistQuery,
    GteQuery,
    GtQuery,
    InQuery,
    LikeQuery,
    LteQuery,
    LtQuery,
    NeqQuery,
    NotQuery,
    OrQuery,
    query_from_str,
    query_to_str,
)


def random_string(length: int) -> str:
    """Generate a random string of given length."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class TestQuery(unittest.TestCase):
    """Test cases for query parsing, serialization, and optimization."""

    # Parse tests
    def test_simple_operator_empty_json_parse(self):
        """Test parsing an empty JSON query."""
        query = query_from_str("{}")
        self.assertEqual(query, AndQuery([]))

    def test_simple_operator_explicit_empty_and_parse(self):
        """Test parsing an explicit empty AND query."""
        query = query_from_str('{"$and": []}')
        self.assertEqual(query, AndQuery([]))

    def test_simple_operator_empty_or_parse(self):
        """Test parsing an empty OR query."""
        query = query_from_str('{"$or": []}')
        self.assertEqual(query, AndQuery([]))

    def test_simple_operator_empty_not_parse(self):
        """Test parsing an empty NOT query."""
        query = query_from_str('{"$not": {}}')
        self.assertEqual(query, NotQuery(AndQuery([])))

    def test_simple_operator_eq_parse(self):
        """Test parsing a simple equality query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": "{value1}"}}')
        self.assertEqual(query, EqQuery(name1, value1))

    def test_simple_operator_eq_with_tilde_parse(self):
        """Test parsing an equality query with '~' prefix."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"~{name1}": "{value1}"}}')
        self.assertEqual(query, EqQuery(f"~{name1}", value1))
        # Note: The '~' character is preserved here but will
        # be ignored and removed in query_to_tagquery

    def test_simple_operator_neq_parse(self):
        """Test parsing a simple inequality query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$neq": "{value1}"}}}}')
        self.assertEqual(query, NeqQuery(name1, value1))

    def test_simple_operator_gt_parse(self):
        """Test parsing a greater-than query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$gt": "{value1}"}}}}')
        self.assertEqual(query, GtQuery(name1, value1))

    def test_simple_operator_gte_parse(self):
        """Test parsing a greater-than-or-equal query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$gte": "{value1}"}}}}')
        self.assertEqual(query, GteQuery(name1, value1))

    def test_simple_operator_lt_parse(self):
        """Test parsing a less-than query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$lt": "{value1}"}}}}')
        self.assertEqual(query, LtQuery(name1, value1))

    def test_simple_operator_lte_parse(self):
        """Test parsing a less-than-or-equal query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$lte": "{value1}"}}}}')
        self.assertEqual(query, LteQuery(name1, value1))

    def test_simple_operator_like_parse(self):
        """Test parsing a LIKE query."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$like": "{value1}"}}}}')
        self.assertEqual(query, LikeQuery(name1, value1))

    def test_simple_operator_in_parse(self):
        """Test parsing an IN query with a single value."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"{name1}": {{"$in": ["{value1}"]}}}}')
        self.assertEqual(query, InQuery(name1, [value1]))

    def test_simple_operator_in_multiple_parse(self):
        """Test parsing an IN query with multiple values."""
        name1 = random_string(10)
        value1, value2, value3 = random_string(10), random_string(10), random_string(10)
        query = query_from_str(
            f'{{"{name1}": {{"$in": ["{value1}", "{value2}", "{value3}"]}}}}'
        )
        self.assertEqual(query, InQuery(name1, [value1, value2, value3]))

    def test_exist_parse_string(self):
        """Test parsing an EXIST query with a single field."""
        name1 = random_string(10)
        query = query_from_str(f'{{"$exist": "{name1}"}}')
        self.assertEqual(query, ExistQuery([name1]))

    def test_exist_parse_array(self):
        """Test parsing an EXIST query with multiple fields."""
        name1, name2 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$exist": ["{name1}", "{name2}"]}}')
        self.assertEqual(query, ExistQuery([name1, name2]))

    def test_and_exist(self):
        """Test parsing an AND query with EXIST subqueries."""
        name1, name2 = random_string(10), random_string(10)
        query = query_from_str(
            f'{{"$and": [{{"$exist": "{name1}"}}, {{"$exist": "{name2}"}}]}}'
        )
        self.assertEqual(query, AndQuery([ExistQuery([name1]), ExistQuery([name2])]))

    def test_and_with_one_eq_parse(self):
        """Test parsing an AND query with a single equality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": "{value1}"}}]}}')
        self.assertEqual(query, AndQuery([EqQuery(name1, value1)]))

    def test_and_with_one_neq_parse(self):
        """Test parsing an AND query with a single inequality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$neq": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([NeqQuery(name1, value1)]))

    def test_and_with_one_gt_parse(self):
        """Test parsing an AND query with a single greater-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$gt": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([GtQuery(name1, value1)]))

    def test_and_with_one_gte_parse(self):
        """Test parsing an AND query with a single greater-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$gte": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([GteQuery(name1, value1)]))

    def test_and_with_one_lt_parse(self):
        """Test parsing an AND query with a single less-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$lt": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([LtQuery(name1, value1)]))

    def test_and_with_one_lte_parse(self):
        """Test parsing an AND query with a single less-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$lte": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([LteQuery(name1, value1)]))

    def test_and_with_one_like_parse(self):
        """Test parsing an AND query with a single LIKE subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$like": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([LikeQuery(name1, value1)]))

    def test_and_with_one_in_parse(self):
        """Test parsing an AND query with a single IN subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"{name1}": {{"$in": ["{value1}"]}}}}]}}')
        self.assertEqual(query, AndQuery([InQuery(name1, [value1])]))

    def test_and_with_one_not_eq_parse(self):
        """Test parsing an AND query with a single NOT equality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$and": [{{"$not": {{"{name1}": "{value1}"}}}}]}}')
        self.assertEqual(query, AndQuery([NotQuery(EqQuery(name1, value1))]))

    def test_short_and_with_multiple_eq_parse(self):
        """Test parsing a short AND query with multiple equality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = query_from_str(
            f'{{"{name1}": "{value1}", "{name2}": "{value2}", "{name3}": "{value3}"}}'
        )
        expected = AndQuery(
            [EqQuery(name1, value1), EqQuery(name2, value2), EqQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_eq_parse(self):
        """Test parsing an AND query with multiple equality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": "{value2}"}}, {{"{name3}": "{value3}"}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [EqQuery(name1, value1), EqQuery(name2, value2), EqQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_neq_parse(self):
        """Test parsing an AND query with multiple inequality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$neq": "{value1}"}}}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$neq": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [NeqQuery(name1, value1), NeqQuery(name2, value2), NeqQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_gt_parse(self):
        """Test parsing an AND query with multiple greater-than subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$gt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [GtQuery(name1, value1), GtQuery(name2, value2), GtQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_gte_parse(self):
        """Test parsing an AND query with multiple greater-than-or-equal subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$gte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gte": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [GteQuery(name1, value1), GteQuery(name2, value2), GteQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_lt_parse(self):
        """Test parsing an AND query with multiple less-than subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$lt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lt": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [LtQuery(name1, value1), LtQuery(name2, value2), LtQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_lte_parse(self):
        """Test parsing an AND query with multiple less-than-or-equal subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$lte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lte": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [LteQuery(name1, value1), LteQuery(name2, value2), LteQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_like_parse(self):
        """Test parsing an AND query with multiple LIKE subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$like": "{value1}"}}}}, '
            f'{{"{name2}": {{"$like": "{value2}"}}}}, '
            f'{{"{name3}": {{"$like": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [LikeQuery(name1, value1), LikeQuery(name2, value2), LikeQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_in_parse(self):
        """Test parsing an AND query with multiple IN subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"{name1}": {{"$in": ["{value1}"]}}}}, '
            f'{{"{name2}": {{"$in": ["{value2}"]}}}}, '
            f'{{"{name3}": {{"$in": ["{value3}"]}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [InQuery(name1, [value1]), InQuery(name2, [value2]), InQuery(name3, [value3])]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_not_eq_parse(self):
        """Test parsing an AND query with multiple NOT equality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": [{{"$not": {{"{name1}": "{value1}"}}}}, '
            f'{{"$not": {{"{name2}": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [
                NotQuery(EqQuery(name1, value1)),
                NotQuery(EqQuery(name2, value2)),
                NotQuery(EqQuery(name3, value3)),
            ]
        )
        self.assertEqual(query, expected)

    def test_and_with_multiple_mixed_parse(self):
        """Test parsing an AND query with mixed subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8a, value8b = random_string(10), random_string(10), random_string(10)
        name9, value9 = random_string(10), random_string(10)
        json_str = (
            f'{{"$and": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}, '
            f'{{"{name4}": {{"$gte": "{value4}"}}}}, '
            f'{{"{name5}": {{"$lt": "{value5}"}}}}, '
            f'{{"{name6}": {{"$lte": "{value6}"}}}}, '
            f'{{"{name7}": {{"$like": "{value7}"}}}}, '
            f'{{"{name8}": {{"$in": ["{value8a}", "{value8b}"]}}}}, '
            f'{{"$not": {{"{name9}": "{value9}"}}}}'
            f"]}}"
        )
        query = query_from_str(json_str)
        expected = AndQuery(
            [
                EqQuery(name1, value1),
                NeqQuery(name2, value2),
                GtQuery(name3, value3),
                GteQuery(name4, value4),
                LtQuery(name5, value5),
                LteQuery(name6, value6),
                LikeQuery(name7, value7),
                InQuery(name8, [value8a, value8b]),
                NotQuery(EqQuery(name9, value9)),
            ]
        )
        self.assertEqual(query, expected)

    def test_or_with_one_eq_parse(self):
        """Test parsing an OR query with a single equality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": "{value1}"}}]}}')
        self.assertEqual(query, OrQuery([EqQuery(name1, value1)]))

    def test_or_with_one_neq_parse(self):
        """Test parsing an OR query with a single inequality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$neq": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([NeqQuery(name1, value1)]))

    def test_or_with_one_gt_parse(self):
        """Test parsing an OR query with a single greater-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$gt": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([GtQuery(name1, value1)]))

    def test_or_with_one_gte_parse(self):
        """Test parsing an OR query with a single greater-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$gte": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([GteQuery(name1, value1)]))

    def test_or_with_one_lt_parse(self):
        """Test parsing an OR query with a single less-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$lt": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([LtQuery(name1, value1)]))

    def test_or_with_one_lte_parse(self):
        """Test parsing an OR query with a single less-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$lte": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([LteQuery(name1, value1)]))

    def test_or_with_one_like_parse(self):
        """Test parsing an OR query with a single LIKE subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$like": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([LikeQuery(name1, value1)]))

    def test_or_with_one_in_parse(self):
        """Test parsing an OR query with a single IN subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"{name1}": {{"$in": ["{value1}"]}}}}]}}')
        self.assertEqual(query, OrQuery([InQuery(name1, [value1])]))

    def test_or_with_one_not_eq_parse(self):
        """Test parsing an OR query with a single NOT equality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$or": [{{"$not": {{"{name1}": "{value1}"}}}}]}}')
        self.assertEqual(query, OrQuery([NotQuery(EqQuery(name1, value1))]))

    def test_or_with_multiple_eq_parse(self):
        """Test parsing an OR query with multiple equality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": "{value2}"}}, {{"{name3}": "{value3}"}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [EqQuery(name1, value1), EqQuery(name2, value2), EqQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_neq_parse(self):
        """Test parsing an OR query with multiple inequality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$neq": "{value1}"}}}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$neq": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [NeqQuery(name1, value1), NeqQuery(name2, value2), NeqQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_gt_parse(self):
        """Test parsing an OR query with multiple greater-than subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$gt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [GtQuery(name1, value1), GtQuery(name2, value2), GtQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_gte_parse(self):
        """Test parsing an OR query with multiple greater-than-or-equal subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$gte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gte": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [GteQuery(name1, value1), GteQuery(name2, value2), GteQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_lt_parse(self):
        """Test parsing an OR query with multiple less-than subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$lt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lt": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [LtQuery(name1, value1), LtQuery(name2, value2), LtQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_lte_parse(self):
        """Test parsing an OR query with multiple less-than-or-equal subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$lte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lte": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [LteQuery(name1, value1), LteQuery(name2, value2), LteQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_like_parse(self):
        """Test parsing an OR query with multiple LIKE subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$like": "{value1}"}}}}, '
            f'{{"{name2}": {{"$like": "{value2}"}}}}, '
            f'{{"{name3}": {{"$like": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [LikeQuery(name1, value1), LikeQuery(name2, value2), LikeQuery(name3, value3)]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_in_parse(self):
        """Test parsing an OR query with multiple IN subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"{name1}": {{"$in": ["{value1}"]}}}}, '
            f'{{"{name2}": {{"$in": ["{value2}"]}}}}, '
            f'{{"{name3}": {{"$in": ["{value3}"]}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [InQuery(name1, [value1]), InQuery(name2, [value2]), InQuery(name3, [value3])]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_not_eq_parse(self):
        """Test parsing an OR query with multiple NOT equality subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": [{{"$not": {{"{name1}": "{value1}"}}}}, '
            f'{{"$not": {{"{name2}": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": "{value3}"}}}}]}}'
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [
                NotQuery(EqQuery(name1, value1)),
                NotQuery(EqQuery(name2, value2)),
                NotQuery(EqQuery(name3, value3)),
            ]
        )
        self.assertEqual(query, expected)

    def test_or_with_multiple_mixed_parse(self):
        """Test parsing an OR query with mixed subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8a, value8b = random_string(10), random_string(10), random_string(10)
        name9, value9 = random_string(10), random_string(10)
        json_str = (
            f'{{"$or": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}, '
            f'{{"{name4}": {{"$gte": "{value4}"}}}}, '
            f'{{"{name5}": {{"$lt": "{value5}"}}}}, '
            f'{{"{name6}": {{"$lte": "{value6}"}}}}, '
            f'{{"{name7}": {{"$like": "{value7}"}}}}, '
            f'{{"{name8}": {{"$in": ["{value8a}", "{value8b}"]}}}}, '
            f'{{"$not": {{"{name9}": "{value9}"}}}}'
            f"]}}"
        )
        query = query_from_str(json_str)
        expected = OrQuery(
            [
                EqQuery(name1, value1),
                NeqQuery(name2, value2),
                GtQuery(name3, value3),
                GteQuery(name4, value4),
                LtQuery(name5, value5),
                LteQuery(name6, value6),
                LikeQuery(name7, value7),
                InQuery(name8, [value8a, value8b]),
                NotQuery(EqQuery(name9, value9)),
            ]
        )
        self.assertEqual(query, expected)

    def test_not_with_one_eq_parse(self):
        """Test parsing a NOT query with a single equality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": "{value1}"}}}}')
        self.assertEqual(query, NotQuery(EqQuery(name1, value1)))

    def test_not_with_one_neq_parse(self):
        """Test parsing a NOT query with a single inequality subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$neq": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(NeqQuery(name1, value1)))

    def test_not_with_one_gt_parse(self):
        """Test parsing a NOT query with a single greater-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$gt": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(GtQuery(name1, value1)))

    def test_not_with_one_gte_parse(self):
        """Test parsing a NOT query with a single greater-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$gte": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(GteQuery(name1, value1)))

    def test_not_with_one_lt_parse(self):
        """Test parsing a NOT query with a single less-than subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$lt": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(LtQuery(name1, value1)))

    def test_not_with_one_lte_parse(self):
        """Test parsing a NOT query with a single less-than-or-equal subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$lte": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(LteQuery(name1, value1)))

    def test_not_with_one_like_parse(self):
        """Test parsing a NOT query with a single LIKE subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$like": "{value1}"}}}}}}')
        self.assertEqual(query, NotQuery(LikeQuery(name1, value1)))

    def test_not_with_one_in_parse(self):
        """Test parsing a NOT query with a single IN subquery."""
        name1, value1 = random_string(10), random_string(10)
        query = query_from_str(f'{{"$not": {{"{name1}": {{"$in": ["{value1}"]}}}}}}')
        self.assertEqual(query, NotQuery(InQuery(name1, [value1])))

    def test_and_or_not_complex_case_parse(self):
        """Test parsing a complex query with AND, OR, and NOT subqueries."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8 = random_string(10), random_string(10)
        json_str = (
            f'{{"$not": {{"$and": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"$or": ['
            f'{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": {{"$lte": "{value3}"}}}}}}, '
            f'{{"$and": ['
            f'{{"{name4}": {{"$lt": "{value4}"}}}}, '
            f'{{"$not": {{"{name5}": {{"$gte": "{value5}"}}}}}}'
            f"]}}"
            f"]}}, "
            f'{{"$not": {{"{name6}": {{"$like": "{value6}"}}}}}}, '
            f'{{"$and": ['
            f'{{"{name7}": "{value7}"}}, '
            f'{{"$not": {{"{name8}": {{"$neq": "{value8}"}}}}}}'
            f"]}}"
            f"]}}}}"
        )
        query = query_from_str(json_str)
        expected = NotQuery(
            AndQuery(
                [
                    EqQuery(name1, value1),
                    OrQuery(
                        [
                            GtQuery(name2, value2),
                            NotQuery(LteQuery(name3, value3)),
                            AndQuery(
                                [
                                    LtQuery(name4, value4),
                                    NotQuery(GteQuery(name5, value5)),
                                ]
                            ),
                        ]
                    ),
                    NotQuery(LikeQuery(name6, value6)),
                    AndQuery([EqQuery(name7, value7), NotQuery(NeqQuery(name8, value8))]),
                ]
            )
        )
        self.assertEqual(query, expected)

    # To string tests
    def test_simple_operator_empty_and_to_string(self):
        """Test converting an empty AND query to a string."""
        query = AndQuery([])
        self.assertEqual(query_to_str(query), "{}")

    def test_simple_operator_eq_to_string(self):
        """Test converting an equality query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = EqQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": "{value1}"}}')

    def test_simple_operator_eq_with_tilde_to_string(self):
        """Test converting an equality query with '~' prefix to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = EqQuery(f"~{name1}", value1)
        self.assertEqual(query_to_str(query), f'{{"~{name1}": "{value1}"}}')
        # Note: The '~' character is preserved in
        # serialization but removed in query_to_tagquery

    def test_simple_operator_neq_to_string(self):
        """Test converting an inequality query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NeqQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$neq": "{value1}"}}}}')

    def test_simple_operator_gt_plaintext_to_string(self):
        """Test converting a greater-than query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = GtQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$gt": "{value1}"}}}}')

    def test_simple_operator_gte_to_string(self):
        """Test converting a greater-than-or-equal query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = GteQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$gte": "{value1}"}}}}')

    def test_simple_operator_lt_to_string(self):
        """Test converting a less-than query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = LtQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$lt": "{value1}"}}}}')

    def test_simple_operator_lte_to_string(self):
        """Test converting a less-than-or-equal query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = LteQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$lte": "{value1}"}}}}')

    def test_simple_operator_like_to_string(self):
        """Test converting a LIKE query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = LikeQuery(name1, value1)
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$like": "{value1}"}}}}')

    def test_simple_operator_in_to_string(self):
        """Test converting an IN query to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = InQuery(name1, [value1])
        self.assertEqual(query_to_str(query), f'{{"{name1}": {{"$in": ["{value1}"]}}}}')

    def test_simple_operator_in_multimply_to_string(self):
        """Test converting an IN query with multiple values to a string."""
        name1 = random_string(10)
        value1, value2, value3 = random_string(10), random_string(10), random_string(10)
        query = InQuery(name1, [value1, value2, value3])
        self.assertEqual(
            query_to_str(query),
            f'{{"{name1}": {{"$in": ["{value1}", "{value2}", "{value3}"]}}}}',
        )

    def test_and_with_one_eq_to_string(self):
        """Test converting an AND query with a single equality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([EqQuery(name1, value1)])
        self.assertEqual(query_to_str(query), f'{{"$and": [{{"{name1}": "{value1}"}}]}}')

    def test_and_with_one_neq_to_string(self):
        """Test converting an AND query with a single inequality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([NeqQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$neq": "{value1}"}}}}]}}'
        )

    def test_and_with_one_gt_to_string(self):
        """Convert query with a single greater-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([GtQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$gt": "{value1}"}}}}]}}'
        )

    def test_and_with_one_gte_to_string(self):
        """Convert AND query with a single greater-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([GteQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$gte": "{value1}"}}}}]}}'
        )

    def test_and_with_one_lt_to_string(self):
        """Convert AND query with a single less-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([LtQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$lt": "{value1}"}}}}]}}'
        )

    def test_and_with_one_lte_to_string(self):
        """Convert AND query with a single less-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([LteQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$lte": "{value1}"}}}}]}}'
        )

    def test_and_with_one_like_to_string(self):
        """Test converting an AND query with a single LIKE subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([LikeQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$like": "{value1}"}}}}]}}'
        )

    def test_and_with_one_in_to_string(self):
        """Test converting an AND query with a single IN subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([InQuery(name1, [value1])])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"{name1}": {{"$in": ["{value1}"]}}}}]}}'
        )

    def test_and_with_one_not_eq_to_string(self):
        """Convert query with a single NOT equality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = AndQuery([NotQuery(EqQuery(name1, value1))])
        self.assertEqual(
            query_to_str(query), f'{{"$and": [{{"$not": {{"{name1}": "{value1}"}}}}]}}'
        )

    def test_and_with_multiple_eq_to_string(self):
        """Convert query with multiple equality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [EqQuery(name1, value1), EqQuery(name2, value2), EqQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": "{value2}"}}, {{"{name3}": "{value3}"}}]}}',
        )

    def test_and_with_multiple_neq_to_string(self):
        """Convert query with multiple inequality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [NeqQuery(name1, value1), NeqQuery(name2, value2), NeqQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$neq": "{value1}"}}}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$neq": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_gt_to_string(self):
        """Convert AND query with multiple greater-than subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [GtQuery(name1, value1), GtQuery(name2, value2), GtQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$gt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_gte_to_string(self):
        """Convert query with multiple greater-than-or-equal subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [GteQuery(name1, value1), GteQuery(name2, value2), GteQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$gte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gte": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_lt_to_string(self):
        """Convert query with multiple less-than subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [LtQuery(name1, value1), LtQuery(name2, value2), LtQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$lt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lt": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_lte_to_string(self):
        """Convert query with multiple less-than-or-equal subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [LteQuery(name1, value1), LteQuery(name2, value2), LteQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$lte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lte": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_like_to_string(self):
        """Test converting an AND query with multiple LIKE subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [LikeQuery(name1, value1), LikeQuery(name2, value2), LikeQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$like": "{value1}"}}}}, '
            f'{{"{name2}": {{"$like": "{value2}"}}}}, '
            f'{{"{name3}": {{"$like": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_in_to_string(self):
        """Test converting an AND query with multiple IN subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [InQuery(name1, [value1]), InQuery(name2, [value2]), InQuery(name3, [value3])]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"{name1}": {{"$in": ["{value1}"]}}}}, '
            f'{{"{name2}": {{"$in": ["{value2}"]}}}}, '
            f'{{"{name3}": {{"$in": ["{value3}"]}}}}]}}',
        )

    def test_and_with_multiple_not_eq_to_string(self):
        """Convert query with multiple NOT equality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = AndQuery(
            [
                NotQuery(EqQuery(name1, value1)),
                NotQuery(EqQuery(name2, value2)),
                NotQuery(EqQuery(name3, value3)),
            ]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$and": [{{"$not": {{"{name1}": "{value1}"}}}}, '
            f'{{"$not": {{"{name2}": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": "{value3}"}}}}]}}',
        )

    def test_and_with_multiple_mixed_to_string(self):
        """Test converting an AND query with mixed subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8a, value8b = random_string(10), random_string(10), random_string(10)
        name9, value9 = random_string(10), random_string(10)
        query = AndQuery(
            [
                EqQuery(name1, value1),
                NeqQuery(name2, value2),
                GtQuery(name3, value3),
                GteQuery(name4, value4),
                LtQuery(name5, value5),
                LteQuery(name6, value6),
                LikeQuery(name7, value7),
                InQuery(name8, [value8a, value8b]),
                NotQuery(EqQuery(name9, value9)),
            ]
        )
        expected = (
            f'{{"$and": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}, '
            f'{{"{name4}": {{"$gte": "{value4}"}}}}, '
            f'{{"{name5}": {{"$lt": "{value5}"}}}}, '
            f'{{"{name6}": {{"$lte": "{value6}"}}}}, '
            f'{{"{name7}": {{"$like": "{value7}"}}}}, '
            f'{{"{name8}": {{"$in": ["{value8a}", "{value8b}"]}}}}, '
            f'{{"$not": {{"{name9}": "{value9}"}}}}'
            f"]}}"
        )
        self.assertEqual(query_to_str(query), expected)

    def test_or_with_one_eq_to_string(self):
        """Test converting an OR query with a single equality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([EqQuery(name1, value1)])
        self.assertEqual(query_to_str(query), f'{{"$or": [{{"{name1}": "{value1}"}}]}}')

    def test_or_with_one_neq_to_string(self):
        """Convert OR query with a single inequality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([NeqQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$neq": "{value1}"}}}}]}}'
        )

    def test_or_with_one_gt_to_string(self):
        """Test converting an OR query with a single greater-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([GtQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$gt": "{value1}"}}}}]}}'
        )

    def test_or_with_one_gte_to_string(self):
        """Convert OR query with a single greater-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([GteQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$gte": "{value1}"}}}}]}}'
        )

    def test_or_with_one_lt_to_string(self):
        """Test converting an OR query with a single less-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([LtQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$lt": "{value1}"}}}}]}}'
        )

    def test_or_with_one_lte_to_string(self):
        """Convert OR query with a single less-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([LteQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$lte": "{value1}"}}}}]}}'
        )

    def test_or_with_one_like_to_string(self):
        """Test converting an OR query with a single LIKE subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([LikeQuery(name1, value1)])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$like": "{value1}"}}}}]}}'
        )

    def test_or_with_one_in_to_string(self):
        """Test converting an OR query with a single IN subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([InQuery(name1, [value1])])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"{name1}": {{"$in": ["{value1}"]}}}}]}}'
        )

    def test_or_with_one_not_eq_to_string(self):
        """Test converting an OR query with a single NOT equality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = OrQuery([NotQuery(EqQuery(name1, value1))])
        self.assertEqual(
            query_to_str(query), f'{{"$or": [{{"$not": {{"{name1}": "{value1}"}}}}]}}'
        )

    def test_or_with_multiple_eq_to_string(self):
        """Test converting an OR query with multiple equality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [EqQuery(name1, value1), EqQuery(name2, value2), EqQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": "{value2}"}}, {{"{name3}": "{value3}"}}]}}',
        )

    def test_or_with_multiple_neq_to_string(self):
        """Test converting an OR query with multiple inequality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [NeqQuery(name1, value1), NeqQuery(name2, value2), NeqQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$neq": "{value1}"}}}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$neq": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_gt_to_string(self):
        """Convert OR query with multiple greater-than subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [GtQuery(name1, value1), GtQuery(name2, value2), GtQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$gt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_gte_to_string(self):
        """Convert OR query with multiple greater-than-or-equal subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [GteQuery(name1, value1), GteQuery(name2, value2), GteQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$gte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$gte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gte": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_lt_to_string(self):
        """Convert OR query with multiple less-than subqueries to a str."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [LtQuery(name1, value1), LtQuery(name2, value2), LtQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$lt": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lt": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lt": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_lte_to_string(self):
        """Convert OR query with multiple less-than-or-equal subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [LteQuery(name1, value1), LteQuery(name2, value2), LteQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$lte": "{value1}"}}}}, '
            f'{{"{name2}": {{"$lte": "{value2}"}}}}, '
            f'{{"{name3}": {{"$lte": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_like_to_string(self):
        """Test converting an OR query with multiple LIKE subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [LikeQuery(name1, value1), LikeQuery(name2, value2), LikeQuery(name3, value3)]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$like": "{value1}"}}}}, '
            f'{{"{name2}": {{"$like": "{value2}"}}}}, '
            f'{{"{name3}": {{"$like": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_in_to_string(self):
        """Test converting an OR query with multiple IN subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [InQuery(name1, [value1]), InQuery(name2, [value2]), InQuery(name3, [value3])]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"{name1}": {{"$in": ["{value1}"]}}}}, '
            f'{{"{name2}": {{"$in": ["{value2}"]}}}}, '
            f'{{"{name3}": {{"$in": ["{value3}"]}}}}]}}',
        )

    def test_or_with_multiple_not_eq_to_string(self):
        """Convert OR query with multiple NOT equality subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        query = OrQuery(
            [
                NotQuery(EqQuery(name1, value1)),
                NotQuery(EqQuery(name2, value2)),
                NotQuery(EqQuery(name3, value3)),
            ]
        )
        self.assertEqual(
            query_to_str(query),
            f'{{"$or": [{{"$not": {{"{name1}": "{value1}"}}}}, '
            f'{{"$not": {{"{name2}": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": "{value3}"}}}}]}}',
        )

    def test_or_with_multiple_mixed_to_string(self):
        """Test converting an OR query with mixed subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8a, value8b = random_string(10), random_string(10), random_string(10)
        name9, value9 = random_string(10), random_string(10)
        query = OrQuery(
            [
                EqQuery(name1, value1),
                NeqQuery(name2, value2),
                GtQuery(name3, value3),
                GteQuery(name4, value4),
                LtQuery(name5, value5),
                LteQuery(name6, value6),
                LikeQuery(name7, value7),
                InQuery(name8, [value8a, value8b]),
                NotQuery(EqQuery(name9, value9)),
            ]
        )
        expected = (
            f'{{"$or": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"{name2}": {{"$neq": "{value2}"}}}}, '
            f'{{"{name3}": {{"$gt": "{value3}"}}}}, '
            f'{{"{name4}": {{"$gte": "{value4}"}}}}, '
            f'{{"{name5}": {{"$lt": "{value5}"}}}}, '
            f'{{"{name6}": {{"$lte": "{value6}"}}}}, '
            f'{{"{name7}": {{"$like": "{value7}"}}}}, '
            f'{{"{name8}": {{"$in": ["{value8a}", "{value8b}"]}}}}, '
            f'{{"$not": {{"{name9}": "{value9}"}}}}'
            f"]}}"
        )
        self.assertEqual(query_to_str(query), expected)

    def test_not_with_one_eq_to_string(self):
        """Test converting a NOT query with a single equality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(EqQuery(name1, value1))
        self.assertEqual(query_to_str(query), f'{{"$not": {{"{name1}": "{value1}"}}}}')

    def test_not_with_one_neq_to_string(self):
        """Test converting a NOT query with a single inequality subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(NeqQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$neq": "{value1}"}}}}}}'
        )

    def test_not_with_one_gt_to_string(self):
        """Test converting a NOT query with a single greater-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(GtQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$gt": "{value1}"}}}}}}'
        )

    def test_not_with_one_gte_to_string(self):
        """Convert NOT query with a single greater-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(GteQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$gte": "{value1}"}}}}}}'
        )

    def test_not_with_one_lt_to_string(self):
        """Test converting a NOT query with a single less-than subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(LtQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$lt": "{value1}"}}}}}}'
        )

    def test_not_with_one_lte_to_string(self):
        """Convert NOT query with a single less-than-or-equal subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(LteQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$lte": "{value1}"}}}}}}'
        )

    def test_not_with_one_like_to_string(self):
        """Test converting a NOT query with a single LIKE subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(LikeQuery(name1, value1))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$like": "{value1}"}}}}}}'
        )

    def test_not_with_one_in_to_string(self):
        """Test converting a NOT query with a single IN subquery to a string."""
        name1, value1 = random_string(10), random_string(10)
        query = NotQuery(InQuery(name1, [value1]))
        self.assertEqual(
            query_to_str(query), f'{{"$not": {{"{name1}": {{"$in": ["{value1}"]}}}}}}'
        )

    def test_and_or_not_complex_case_to_string(self):
        """Convert complex query with AND, OR, and NOT subqueries to a string."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        name3, value3 = random_string(10), random_string(10)
        name4, value4 = random_string(10), random_string(10)
        name5, value5 = random_string(10), random_string(10)
        name6, value6 = random_string(10), random_string(10)
        name7, value7 = random_string(10), random_string(10)
        name8, value8 = random_string(10), random_string(10)
        query = NotQuery(
            AndQuery(
                [
                    EqQuery(name1, value1),
                    OrQuery(
                        [
                            GtQuery(name2, value2),
                            NotQuery(LteQuery(name3, value3)),
                            AndQuery(
                                [
                                    LtQuery(name4, value4),
                                    NotQuery(GteQuery(name5, value5)),
                                ]
                            ),
                        ]
                    ),
                    NotQuery(LikeQuery(name6, value6)),
                    AndQuery([EqQuery(name7, value7), NotQuery(NeqQuery(name8, value8))]),
                ]
            )
        )
        expected = (
            f'{{"$not": {{"$and": ['
            f'{{"{name1}": "{value1}"}}, '
            f'{{"$or": [{{"{name2}": {{"$gt": "{value2}"}}}}, '
            f'{{"$not": {{"{name3}": {{"$lte": "{value3}"}}}}}}, '
            f'{{"$and": [{{"{name4}": {{"$lt": "{value4}"}}}}, '
            f'{{"$not": {{"{name5}": {{"$gte": "{value5}"}}}}}}]}}]}}, '
            f'{{"$not": {{"{name6}": {{"$like": "{value6}"}}}}}}, '
            f'{{"$and": [{{"{name7}": "{value7}"}}, '
            f'{{"$not": {{"{name8}": {{"$neq": "{value8}"}}}}}}]}}]}}}}'
        )
        self.assertEqual(query_to_str(query), expected)

    def test_old_format(self):
        """Test parsing a query in the old format."""
        name1, value1 = random_string(10), random_string(10)
        name2, value2 = random_string(10), random_string(10)
        query = query_from_str(f'[{{"{name1}": "{value1}"}}, {{"{name2}": "{value2}"}}]')
        self.assertEqual(query, OrQuery([EqQuery(name1, value1), EqQuery(name2, value2)]))

    def test_old_format_empty(self):
        """Test parsing an empty query in the old format."""
        query = query_from_str("[]")
        self.assertEqual(query, AndQuery([]))

    def test_old_format_with_nulls(self):
        """Test parsing a query in the old format with null values."""
        name1, value1 = random_string(10), random_string(10)
        name2 = random_string(10)
        query = query_from_str(f'[{{"{name1}": "{value1}"}}, {{"{name2}": null}}]')
        self.assertEqual(query, OrQuery([EqQuery(name1, value1)]))

    def test_optimise_and(self):
        """Test optimizing an empty AND query."""
        query = query_from_str("{}")
        self.assertIsNone(query.optimise())

    def test_optimise_or(self):
        """Test optimizing an empty OR query."""
        query = query_from_str("[]")
        self.assertIsNone(query.optimise())

    def test_optimise_single_nested_and(self):
        """Test optimizing a single nested AND query."""
        query = query_from_str('{"$and": [{"$and": []}]}')
        self.assertIsNone(query.optimise())

    def test_optimise_several_nested_and(self):
        """Test optimizing several nested AND queries."""
        query = query_from_str('{"$and": [{"$and": []}, {"$and": []}]}')
        self.assertIsNone(query.optimise())

    def test_optimise_single_nested_or(self):
        """Test optimizing a single nested OR query."""
        query = query_from_str('{"$and": [{"$or": []}]}')
        self.assertIsNone(query.optimise())

    def test_optimise_several_nested_or(self):
        """Test optimizing several nested OR queries."""
        query = query_from_str('{"$and": [{"$or": []}, {"$or": []}]}')
        self.assertIsNone(query.optimise())


if __name__ == "__main__":
    unittest.main()
