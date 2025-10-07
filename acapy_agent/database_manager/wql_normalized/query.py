"""Askar WQL (Wallet Query Language) parsing and optimization."""

import json
from typing import Callable, List, Optional, Set, Tuple

# JSONValue represents a parsed JSON value, which can be a dict, list, str, or None
JSONValue = dict | list | str | None


class Query:
    """Base class for all query types."""

    def optimise(self) -> Optional["Query"]:
        """Optimize the query by simplifying its structure."""
        raise NotImplementedError

    def map(
        self, key_func: Callable[[str], str], value_func: Callable[[str, str], str]
    ) -> "Query":
        """Transform keys and values in the query."""
        raise NotImplementedError

    def map_names(self, key_func: Callable[[str], str]) -> "Query":
        """Transform only the keys in the query."""
        return self.map(key_func, lambda k, v: v)

    def map_values(self, value_func: Callable[[str, str], str]) -> "Query":
        """Transform only the values in the query."""
        return self.map(lambda k: k, value_func)

    def to_dict(self) -> dict:
        """Convert the query to a JSON-compatible dictionary."""
        raise NotImplementedError

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Convert the query to an SQL condition and parameters.

        Args:
            table_columns (Optional[Set[str]]): Set of valid column names for validation.

        Returns:
            Tuple[str, List[Union[str, int, float]]]: SQL condition string and
                list of parameters.

        """
        raise NotImplementedError

    def __eq__(self, other):
        """Check equality with another Query object."""
        return NotImplemented


class AndQuery(Query):
    """Logical AND of multiple clauses."""

    def __init__(self, subqueries: List[Query]):
        """Initialize AndQuery."""
        self.subqueries = subqueries

    def optimise(self) -> Optional[Query]:
        """Perform the action."""
        optimised = [
            q for q in (sq.optimise() for sq in self.subqueries) if q is not None
        ]
        if not optimised:
            return None
        elif len(optimised) == 1:
            return optimised[0]
        else:
            return AndQuery(optimised)

    def map(self, key_func, value_func):
        """Perform the action."""
        return AndQuery([sq.map(key_func, value_func) for sq in self.subqueries])

    def to_dict(self):
        """Perform the action."""
        if not self.subqueries:
            return {}
        return {"$and": [sq.to_dict() for sq in self.subqueries]}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if not self.subqueries:
            return "1=1", []  # True for empty AND
        sub_sqls = [sq.to_sql(table_columns) for sq in self.subqueries]
        conditions = [s[0] for s in sub_sqls]
        params = [p for s in sub_sqls for p in s[1]]
        return "(" + " AND ".join(conditions) + ")", params

    def __eq__(self, other):
        """Magic method description."""
        return isinstance(other, AndQuery) and self.subqueries == other.subqueries


class OrQuery(Query):
    """Logical OR of multiple clauses."""

    def __init__(self, subqueries: List[Query]):
        """Initialize OrQuery."""
        self.subqueries = subqueries

    def optimise(self) -> Optional[Query]:
        """Perform the action."""
        optimised = [
            q for q in (sq.optimise() for sq in self.subqueries) if q is not None
        ]
        if not optimised:
            return None
        elif len(optimised) == 1:
            return optimised[0]
        else:
            return OrQuery(optimised)

    def map(self, key_func, value_func):
        """Perform the action."""
        return OrQuery([sq.map(key_func, value_func) for sq in self.subqueries])

    def to_dict(self):
        """Perform the action."""
        if not self.subqueries:
            return {}
        return {"$or": [sq.to_dict() for sq in self.subqueries]}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if not self.subqueries:
            return "1=0", []  # False for empty OR
        sub_sqls = [sq.to_sql(table_columns) for sq in self.subqueries]
        conditions = [s[0] for s in sub_sqls]
        params = [p for s in sub_sqls for p in s[1]]
        return "(" + " OR ".join(conditions) + ")", params

    def __eq__(self, other):
        """Magic method description."""
        return isinstance(other, OrQuery) and self.subqueries == other.subqueries


class NotQuery(Query):
    """Negation of a clause."""

    def __init__(self, subquery: Query):
        """Initialize NotQuery."""
        self.subquery = subquery

    def optimise(self) -> Optional[Query]:
        """Perform the action."""
        opt_sub = self.subquery.optimise()
        if opt_sub is None:
            return None
        elif isinstance(opt_sub, NotQuery):
            return opt_sub.subquery
        else:
            return NotQuery(opt_sub)

    def map(self, key_func, value_func):
        """Perform the action."""
        return NotQuery(self.subquery.map(key_func, value_func))

    def to_dict(self):
        """Perform the action."""
        return {"$not": self.subquery.to_dict()}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        sub_sql, sub_params = self.subquery.to_sql(table_columns)
        return f"NOT ({sub_sql})", sub_params

    def __eq__(self, other):
        """Magic method description."""
        return isinstance(other, NotQuery) and self.subquery == other.subquery


class EqQuery(Query):
    """Equality comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize EqQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return EqQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: self.value}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} = ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, EqQuery)
            and self.key == other.key
            and self.value == other.value
        )


class NeqQuery(Query):
    """Inequality comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize NeqQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return NeqQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$neq": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} != ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, NeqQuery)
            and self.key == other.key
            and self.value == other.value
        )


class GtQuery(Query):
    """Greater-than comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize GtQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return GtQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$gt": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} > ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, GtQuery)
            and self.key == other.key
            and self.value == other.value
        )


class GteQuery(Query):
    """Greater-than-or-equal comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize GteQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return GteQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$gte": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} >= ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, GteQuery)
            and self.key == other.key
            and self.value == other.value
        )


class LtQuery(Query):
    """Less-than comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize LtQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return LtQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$lt": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} < ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, LtQuery)
            and self.key == other.key
            and self.value == other.value
        )


class LteQuery(Query):
    """Less-than-or-equal comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize LteQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return LteQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$lte": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} <= ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, LteQuery)
            and self.key == other.key
            and self.value == other.value
        )


class LikeQuery(Query):
    """SQL 'LIKE'-compatible string comparison for a field value."""

    def __init__(self, key: str, value: str):
        """Initialize LikeQuery."""
        self.key = key
        self.value = value

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return LikeQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$like": self.value}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        return f"{self.key} LIKE ?", [self.value]

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, LikeQuery)
            and self.key == other.key
            and self.value == other.value
        )


class InQuery(Query):
    """Match one of multiple field values in a set."""

    def __init__(self, key: str, values: List[str]):
        """Initialize InQuery."""
        self.key = key
        self.values = values

    def optimise(self):
        """Perform the action."""
        if len(self.values) == 1:
            return EqQuery(self.key, self.values[0])
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        new_values = [value_func(self.key, v) for v in self.values]
        return InQuery(key_func(self.key), new_values)

    def to_dict(self):
        """Perform the action."""
        return {self.key: {"$in": self.values}}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if table_columns and self.key not in table_columns:
            raise ValueError(f"Invalid column name: {self.key}")
        placeholders = ", ".join(["?" for _ in self.values])
        return f"{self.key} IN ({placeholders})", self.values

    def __eq__(self, other):
        """Magic method description."""
        return (
            isinstance(other, InQuery)
            and self.key == other.key
            and self.values == other.values
        )


class ExistQuery(Query):
    """Match any non-null field value of the given field names."""

    def __init__(self, keys: List[str]):
        """Initialize ExistQuery."""
        self.keys = keys

    def optimise(self):
        """Perform the action."""
        return self

    def map(self, key_func, value_func):
        """Perform the action."""
        return ExistQuery([key_func(k) for k in self.keys])

    def to_dict(self):
        """Perform the action."""
        return {"$exist": self.keys}

    def to_sql(
        self, table_columns: Optional[Set[str]] = None
    ) -> Tuple[str, List[str | int | float]]:
        """Perform the action."""
        if len(self.keys) != 1:
            raise ValueError("Exist query must have exactly one key")
        key = self.keys[0]
        if table_columns and key not in table_columns:
            raise ValueError(f"Invalid column name: {key}")
        return f"{key} IS NOT NULL", []

    def __eq__(self, other):
        """Magic method description."""
        return isinstance(other, ExistQuery) and self.keys == other.keys


def parse_single_operator(op_name: str, key: str, value: JSONValue) -> Query:
    """Parse a single operator from a key-value pair."""

    def _require_str(val: JSONValue, opname: str) -> str:
        if not isinstance(val, str):
            raise ValueError(f"{opname} must be used with string")
        return val

    def _require_str_list(val: JSONValue, opname: str) -> List[str]:
        if not (isinstance(val, list) and all(isinstance(v, str) for v in val)):
            raise ValueError(f"{opname} must be used with array of strings")
        return val

    str_ops = {
        "$neq": NeqQuery,
        "$gt": GtQuery,
        "$gte": GteQuery,
        "$lt": LtQuery,
        "$lte": LteQuery,
        "$like": LikeQuery,
    }
    if op_name in str_ops:
        return str_ops[op_name](key, _require_str(value, op_name))
    if op_name == "$in":
        return InQuery(key, _require_str_list(value, "$in"))
    raise ValueError("Unknown operator")


def parse_operator(key: str, value: JSONValue) -> Optional[Query]:
    """Parse an operator from a key-value pair."""

    def _parse_array_of_dicts(val: JSONValue, opname: str) -> List[Query]:
        if not isinstance(val, list):
            raise ValueError(f"{opname} must be an array")
        return [parse_query(v) for v in val if isinstance(v, dict)]

    def _parse_and(val: JSONValue) -> Optional[Query]:
        subs = _parse_array_of_dicts(val, "$and")
        return AndQuery(subs) if subs else None

    def _parse_or(val: JSONValue) -> Optional[Query]:
        subs = _parse_array_of_dicts(val, "$or")
        return OrQuery(subs) if subs else None

    def _parse_not(val: JSONValue) -> Query:
        if not isinstance(val, dict):
            raise ValueError("$not must be a JSON object")
        return NotQuery(parse_query(val))

    def _parse_exist(val: JSONValue) -> Optional[Query]:
        if isinstance(val, str):
            keys = [val]
        elif isinstance(val, list):
            keys = [k for k in val if isinstance(k, str)]
            if not keys:
                return None
        else:
            raise ValueError("$exist must be a string or array of strings")
        return ExistQuery(keys)

    dispatch = {
        "$and": _parse_and,
        "$or": _parse_or,
        "$not": _parse_not,
        "$exist": _parse_exist,
    }
    if key in dispatch:
        return dispatch[key](value)

    if isinstance(value, str):
        return EqQuery(key, value)
    if isinstance(value, dict) and len(value) == 1:
        op_name, op_value = next(iter(value.items()))
        return parse_single_operator(op_name, key, op_value)
    raise ValueError("Unsupported value")


def parse_query(query_dict: dict) -> Query:
    """Parse a dictionary into a Query object."""
    operators = []
    for key, value in query_dict.items():
        operator = parse_operator(key, value)
        if operator is not None:
            operators.append(operator)
    if not operators:
        return AndQuery([])
    elif len(operators) == 1:
        return operators[0]
    else:
        return AndQuery(operators)


def query_from_json(json_value: JSONValue) -> Query:
    """Parse a JSON value (dict or list) into a Query object."""
    if isinstance(json_value, dict):
        return parse_query(json_value)
    elif isinstance(json_value, list):
        sub_queries = []
        for item in json_value:
            if isinstance(item, dict):
                sub_query_dict = {k: v for k, v in item.items() if v is not None}
                if sub_query_dict:
                    sub_queries.append(parse_query(sub_query_dict))
        if sub_queries:
            return OrQuery(sub_queries)
        return AndQuery([])  # Empty list defaults to an empty AND (true)
    else:
        raise ValueError("Query must be a JSON object or array")


def query_from_str(json_str: str) -> Query:
    """Parse a JSON string into a Query object."""
    if isinstance(json_str, str):
        json_value = json.loads(json_str)
    elif isinstance(json_str, dict):
        json_value = json_str
    else:
        raise ValueError("Input must be a JSON string or a dictionary")
    return query_from_json(json_value)


def query_to_str(query: Query) -> str:
    """Convert a Query object to a JSON string."""
    return json.dumps(query.to_dict())


if __name__ == "__main__":
    # Example usage
    json_str = '{"name": "value", "age": {"$gt": "30"}}'
    query = query_from_str(json_str)
    print(f"Parsed query: {query.to_dict()}")
    optimized = query.optimise()
    print(f"Optimized query: {optimized.to_dict() if optimized else None}")
    # Example SQL translation
    sql, params = query.to_sql()
    print(f"SQL: {sql}, Params: {params}")
