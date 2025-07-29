"""Askar WQL (Wallet Query Language) parsing and optimization."""

from typing import List, Optional, Callable, Union
import json

# JSONValue represents a parsed JSON value, which can be a dict, list, str, or None
JSONValue = Union[dict, list, str, None]


class Query:
    """Base class for all query types."""

    def optimise(self) -> Optional['Query']:
        """Optimize the query by simplifying its structure."""
        raise NotImplementedError

    def map(self, key_func: Callable[[str], str], value_func: Callable[[str, str], str]) -> 'Query':
        """Transform keys and values in the query."""
        raise NotImplementedError

    def map_names(self, key_func: Callable[[str], str]) -> 'Query':
        """Transform only the keys in the query."""
        return self.map(key_func, lambda k, v: v)

    def map_values(self, value_func: Callable[[str, str], str]) -> 'Query':
        """Transform only the values in the query."""
        return self.map(lambda k: k, value_func)

    def to_dict(self) -> dict:
        """Convert the query to a JSON-compatible dictionary."""
        raise NotImplementedError

    def __eq__(self, other):
        raise NotImplementedError


class AndQuery(Query):
    """Logical AND of multiple clauses."""

    def __init__(self, subqueries: List[Query]):
        self.subqueries = subqueries

    def optimise(self) -> Optional[Query]:
        optimised = [q for q in (sq.optimise() for sq in self.subqueries) if q is not None]
        if not optimised:
            return None
        elif len(optimised) == 1:
            return optimised[0]
        else:
            return AndQuery(optimised)

    def map(self, key_func, value_func):
        return AndQuery([sq.map(key_func, value_func) for sq in self.subqueries])

    def to_dict(self):
        if not self.subqueries:
            return {}
        return {"$and": [sq.to_dict() for sq in self.subqueries]}

    def __eq__(self, other):
        return isinstance(other, AndQuery) and self.subqueries == other.subqueries


class OrQuery(Query):
    """Logical OR of multiple clauses."""

    def __init__(self, subqueries: List[Query]):
        self.subqueries = subqueries

    def optimise(self) -> Optional[Query]:
        optimised = [q for q in (sq.optimise() for sq in self.subqueries) if q is not None]
        if not optimised:
            return None
        elif len(optimised) == 1:
            return optimised[0]
        else:
            return OrQuery(optimised)

    def map(self, key_func, value_func):
        return OrQuery([sq.map(key_func, value_func) for sq in self.subqueries])

    def to_dict(self):
        if not self.subqueries:
            return {}
        return {"$or": [sq.to_dict() for sq in self.subqueries]}

    def __eq__(self, other):
        return isinstance(other, OrQuery) and self.subqueries == other.subqueries


class NotQuery(Query):
    """Negation of a clause."""

    def __init__(self, subquery: Query):
        self.subquery = subquery

    def optimise(self) -> Optional[Query]:
        opt_sub = self.subquery.optimise()
        if opt_sub is None:
            return None
        elif isinstance(opt_sub, NotQuery):
            return opt_sub.subquery
        else:
            return NotQuery(opt_sub)

    def map(self, key_func, value_func):
        return NotQuery(self.subquery.map(key_func, value_func))

    def to_dict(self):
        return {"$not": self.subquery.to_dict()}

    def __eq__(self, other):
        return isinstance(other, NotQuery) and self.subquery == other.subquery


class EqQuery(Query):
    """Equality comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return EqQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: self.value}

    def __eq__(self, other):
        return isinstance(other, EqQuery) and self.key == other.key and self.value == other.value


class NeqQuery(Query):
    """Inequality comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return NeqQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$neq": self.value}}

    def __eq__(self, other):
        return isinstance(other, NeqQuery) and self.key == other.key and self.value == other.value


class GtQuery(Query):
    """Greater-than comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return GtQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$gt": self.value}}

    def __eq__(self, other):
        return isinstance(other, GtQuery) and self.key == other.key and self.value == other.value


class GteQuery(Query):
    """Greater-than-or-equal comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return GteQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$gte": self.value}}

    def __eq__(self, other):
        return isinstance(other, GteQuery) and self.key == other.key and self.value == other.value


class LtQuery(Query):
    """Less-than comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return LtQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$lt": self.value}}

    def __eq__(self, other):
        return isinstance(other, LtQuery) and self.key == other.key and self.value == other.value


class LteQuery(Query):
    """Less-than-or-equal comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return LteQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$lte": self.value}}

    def __eq__(self, other):
        return isinstance(other, LteQuery) and self.key == other.key and self.value == other.value


class LikeQuery(Query):
    """SQL 'LIKE'-compatible string comparison for a field value."""

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return LikeQuery(key_func(self.key), value_func(self.key, self.value))

    def to_dict(self):
        return {self.key: {"$like": self.value}}

    def __eq__(self, other):
        return isinstance(other, LikeQuery) and self.key == other.key and self.value == other.value


class InQuery(Query):
    """Match one of multiple field values in a set."""

    def __init__(self, key: str, values: List[str]):
        self.key = key
        self.values = values

    def optimise(self):
        if len(self.values) == 1:
            return EqQuery(self.key, self.values[0])
        return self

    def map(self, key_func, value_func):
        return InQuery(key_func(self.key), [value_func(self.key, v) for v in self.values])

    def to_dict(self):
        return {self.key: {"$in": self.values}}

    def __eq__(self, other):
        return isinstance(other, InQuery) and self.key == other.key and self.values == other.values


class ExistQuery(Query):
    """Match any non-null field value of the given field names."""

    def __init__(self, keys: List[str]):
        self.keys = keys

    def optimise(self):
        return self

    def map(self, key_func, value_func):
        return ExistQuery([key_func(k) for k in self.keys])

    def to_dict(self):
        return {"$exist": self.keys}

    def __eq__(self, other):
        return isinstance(other, ExistQuery) and self.keys == other.keys


def parse_single_operator(op_name: str, key: str, value: JSONValue) -> Query:
    """Parse a single operator from a key-value pair."""
    if op_name == "$neq":
        if not isinstance(value, str):
            raise ValueError("$neq must be used with string")
        return NeqQuery(key, value)
    elif op_name == "$gt":
        if not isinstance(value, str):
            raise ValueError("$gt must be used with string")
        return GtQuery(key, value)
    elif op_name == "$gte":
        if not isinstance(value, str):
            raise ValueError("$gte must be used with string")
        return GteQuery(key, value)
    elif op_name == "$lt":
        if not isinstance(value, str):
            raise ValueError("$lt must be used with string")
        return LtQuery(key, value)
    elif op_name == "$lte":
        if not isinstance(value, str):
            raise ValueError("$lte must be used with string")
        return LteQuery(key, value)
    elif op_name == "$like":
        if not isinstance(value, str):
            raise ValueError("$like must be used with string")
        return LikeQuery(key, value)
    elif op_name == "$in":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError("$in must be used with array of strings")
        return InQuery(key, value)
    else:
        raise ValueError("Unknown operator")


def parse_operator(key: str, value: JSONValue) -> Optional[Query]:
    """Parse an operator from a key-value pair."""
    if key == "$and":
        if not isinstance(value, list):
            raise ValueError("$and must be an array")
        subqueries = [parse_query(sub_dict) for sub_dict in value if isinstance(sub_dict, dict)]
        if not subqueries:
            return None
        return AndQuery(subqueries)
    elif key == "$or":
        if not isinstance(value, list):
            raise ValueError("$or must be an array")
        subqueries = [parse_query(sub_dict) for sub_dict in value if isinstance(sub_dict, dict)]
        if not subqueries:
            return None
        return OrQuery(subqueries)
    elif key == "$not":
        if not isinstance(value, dict):
            raise ValueError("$not must be a JSON object")
        return NotQuery(parse_query(value))
    elif key == "$exist":
        if isinstance(value, str):
            keys = [value]
        elif isinstance(value, list):
            keys = [k for k in value if isinstance(k, str)]
            if not keys:
                return None
        else:
            raise ValueError("$exist must be a string or array of strings")
        return ExistQuery(keys)
    else:
        if isinstance(value, str):
            return EqQuery(key, value)
        elif isinstance(value, dict) and len(value) == 1:
            op_name, op_value = next(iter(value.items()))
            return parse_single_operator(op_name, key, op_value)
        else:
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


# def query_from_json(json_value: JSONValue) -> Query:
#     """Parse a JSON value (dict or list) into a Query object."""
#     if isinstance(json_value, dict):
#         return parse_query(json_value)
#     elif isinstance(json_value, list):
#         sub_queries = []
#         for item in json_value:
#             if isinstance(item, dict):
#                 sub_query_dict = {k: v for k, v in item.items() if v is not None}
#                 if sub_query_dict:
#                     sub_queries.append(parse_query(sub_query_dict))
#         if sub_queries:
#             return OrQuery(sub_queries)
#         return AndQuery([])
#     else:
#         raise ValueError("Query must be a JSON object or array")

def query_from_json(json_value: JSONValue) -> Query:
    """Parse a JSON value (dict or list) into a Query object."""
    if isinstance(json_value, dict):
        return parse_query(json_value)
    elif isinstance(json_value, list):
        sub_queries = []
        for item in json_value:
            if isinstance(item, dict):
                # Filter out null values, consistent with original WQL behavior
                sub_query_dict = {k: v for k, v in item.items() if v is not None}
                if sub_query_dict:  # Only add non-empty subqueries
                    sub_queries.append(parse_query(sub_query_dict))
        if sub_queries:
            return OrQuery(sub_queries)
        return AndQuery([])  # Empty list defaults to an empty AND (true)
    else:
        raise ValueError("Query must be a JSON object or array")

#Need to support 3 kinds of query
# simple query  {'cred_def_id': 'WgWxqztrNooG92RXvxSTWv:3:CL:20:tag'} this will become $and
# older format where the query is an array of objects ([{"field1": "value1"}, {"field2": "value2"}]). this will become $or.
# complex query like, and, in etc..
tag_filter = '{"attr::person.gender": {"$like": "F"}}'
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