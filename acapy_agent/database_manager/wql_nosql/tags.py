"""Module docstring."""

import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import List

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
)


class TagName:
    """Represents a tag name for WQL queries."""

    def __init__(self, value):
        """Initialize TagName with a value."""
        self.value = value

    def to_string(self):
        """Perform the action."""
        return self.value

    def __eq__(self, other):
        """Magic method description."""
        return self.value == other.value

    def __repr__(self):
        """Magic method description."""
        return f"TagName(value='{self.value}')"


class CompareOp(Enum):
    """Class description."""

    Eq = "="
    Neq = "!="
    Gt = ">"
    Gte = ">="
    Lt = "<"
    Lte = "<="
    Like = "LIKE"

    def as_sql_str(self):
        """Perform the action."""
        return self.value

    def as_sql_str_for_prefix(self):
        """Perform the action."""
        if self in [
            CompareOp.Eq,
            CompareOp.Neq,
            CompareOp.Gt,
            CompareOp.Gte,
            CompareOp.Lt,
            CompareOp.Lte,
        ]:
            return self.value
        return None


class ConjunctionOp(Enum):
    """Class description."""

    And = " AND "
    Or = " OR "

    def as_sql_str(self):
        """Perform the action."""
        return self.value

    def negate(self):
        """Perform the action."""
        if self == ConjunctionOp.And:
            return ConjunctionOp.Or
        elif self == ConjunctionOp.Or:
            return ConjunctionOp.And


class TagQuery:
    """Class description."""

    def __init__(
        self,
        variant: str,
        data: "TagQuery" | List["TagQuery"] | TagName | str | List[str],
    ):
        """Initialize TagQuery."""
        self.variant = variant
        self.data = data

    def __repr__(self):
        """Magic method description."""
        if isinstance(self.data, list):
            data_repr = [repr(d) for d in self.data]
            data_str = "[" + ", ".join(data_repr) + "]"
        elif isinstance(self.data, (TagQuery, TagName)):
            data_str = repr(self.data)
        else:
            data_str = f"'{self.data}'"
        return f"TagQuery(variant='{self.variant}', data={data_str})"

    @staticmethod
    def eq(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Eq", (name, value))

    @staticmethod
    def neq(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Neq", (name, value))

    @staticmethod
    def gt(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Gt", (name, value))

    @staticmethod
    def gte(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Gte", (name, value))

    @staticmethod
    def lt(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Lt", (name, value))

    @staticmethod
    def lte(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Lte", (name, value))

    @staticmethod
    def like(name: TagName, value: str):
        """Perform the action."""
        return TagQuery("Like", (name, value))

    @staticmethod
    def in_(name: TagName, values: List[str]):
        """Perform the action."""
        return TagQuery("In", (name, values))

    @staticmethod
    def exist(names: List[TagName]):
        """Perform the action."""
        return TagQuery("Exist", names)

    @staticmethod
    def and_(subqueries: List["TagQuery"]):
        """Perform the action."""
        return TagQuery("And", subqueries)

    @staticmethod
    def or_(subqueries: List["TagQuery"]):
        """Perform the action."""
        return TagQuery("Or", subqueries)

    @staticmethod
    def not_(subquery: "TagQuery"):
        """Perform the action."""
        return TagQuery("Not", subquery)

    def to_wql_dict(self):
        """Convert the TagQuery to a WQL-compatible dictionary."""
        if self.variant == "Eq":
            name, value = self.data
            return {name.to_string(): value}
        elif self.variant == "Neq":
            name, value = self.data
            return {name.to_string(): {"$neq": value}}
        elif self.variant == "Gt":
            name, value = self.data
            return {name.to_string(): {"$gt": value}}
        elif self.variant == "Gte":
            name, value = self.data
            return {name.to_string(): {"$gte": value}}
        elif self.variant == "Lt":
            name, value = self.data
            return {name.to_string(): {"$lt": value}}
        elif self.variant == "Lte":
            name, value = self.data
            return {name.to_string(): {"$lte": value}}
        elif self.variant == "Like":
            name, value = self.data
            return {name.to_string(): {"$like": value}}
        elif self.variant == "In":
            name, values = self.data
            return {name.to_string(): {"$in": values}}
        elif self.variant == "Exist":
            names = self.data
            return {"$exist": [name.to_string() for name in names]}
        elif self.variant == "And":
            subqueries = self.data
            if not subqueries:
                return {}
            return {"$and": [sq.to_wql_dict() for sq in subqueries]}
        elif self.variant == "Or":
            subqueries = self.data
            if not subqueries:
                return {}
            return {"$or": [sq.to_wql_dict() for sq in subqueries]}
        elif self.variant == "Not":
            subquery = self.data
            return {"$not": subquery.to_wql_dict()}
        else:
            raise ValueError(f"Unknown query variant: {self.variant}")

    def to_wql_str(self):
        """Convert the TagQuery to a WQL JSON string."""
        return json.dumps(self.to_wql_dict())


class TagQueryEncoder(ABC):
    """Class description."""

    @abstractmethod
    def encode_name(self, name: TagName) -> bytes:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_value(self, value: str) -> bytes:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_op_clause(
        self, op: CompareOp, enc_name: bytes, enc_value: bytes, negate: bool
    ) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_in_clause(
        self, enc_name: bytes, enc_values: List[bytes], negate: bool
    ) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_exist_clause(self, enc_name: bytes, negate: bool) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        """Perform the action."""
        pass

    def encode_query(self, query: TagQuery, negate: bool = False) -> str:
        """Encode a TagQuery using mapping-based dispatch to reduce branching."""
        compare_map = {
            "Eq": CompareOp.Eq,
            "Neq": CompareOp.Neq,
            "Gt": CompareOp.Gt,
            "Gte": CompareOp.Gte,
            "Lt": CompareOp.Lt,
            "Lte": CompareOp.Lte,
            "Like": CompareOp.Like,
        }
        if query.variant in compare_map:
            return self.encode_op(compare_map[query.variant], *query.data, negate)
        if query.variant == "In":
            return self.encode_in(*query.data, negate)
        if query.variant == "Exist":
            return self.encode_exist(query.data, negate)
        if query.variant in ["And", "Or"]:
            op = ConjunctionOp.And if query.variant == "And" else ConjunctionOp.Or
            return self.encode_conj(op, query.data, negate)
        if query.variant == "Not":
            return self.encode_query(query.data, not negate)
        raise ValueError("Unknown query variant")

    def encode_op(self, op: CompareOp, name: TagName, value: str, negate: bool):
        """Perform the action."""
        enc_name = self.encode_name(name)
        enc_value = self.encode_value(value)
        return self.encode_op_clause(op, enc_name, enc_value, negate)

    def encode_in(self, name: TagName, values: List[str], negate: bool):
        """Perform the action."""
        enc_name = self.encode_name(name)
        enc_values = [self.encode_value(v) for v in values]
        return self.encode_in_clause(enc_name, enc_values, negate)

    def encode_exist(self, names: List[TagName], negate: bool):
        """Perform the action."""
        if not names:
            return None
        elif len(names) == 1:
            enc_name = self.encode_name(names[0])
            return self.encode_exist_clause(enc_name, negate)
        else:
            clauses = [self.encode_exist([name], negate) for name in names]
            return self.encode_conj_clause(ConjunctionOp.And, [c for c in clauses if c])

    def encode_conj(self, op: ConjunctionOp, subqueries: List[TagQuery], negate: bool):
        """Perform the action."""
        op = op.negate() if negate else op
        clauses = []
        for q in subqueries:
            clause = self.encode_query(q, negate)
            if clause is not None:
                clauses.append(clause)
        return self.encode_conj_clause(op, clauses)


def query_to_tagquery(q):
    """Convert a Query object from query.py to a TagQuery object from tags.py.

    Strips '~' from keys as it is no longer used to determine tag type.
    NOTE: this is for backward compatibility as the caller will continue to
    provide the ~ character for plaintext.
    """
    if isinstance(q, AndQuery):
        return TagQuery.and_([query_to_tagquery(sq) for sq in q.subqueries])
    elif isinstance(q, OrQuery):
        return TagQuery.or_([query_to_tagquery(sq) for sq in q.subqueries])
    elif isinstance(q, NotQuery):
        return TagQuery.not_(query_to_tagquery(q.subquery))
    elif isinstance(q, EqQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.eq(tag_name, q.value)
    elif isinstance(q, NeqQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.neq(tag_name, q.value)
    elif isinstance(q, GtQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.gt(tag_name, q.value)
    elif isinstance(q, GteQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.gte(tag_name, q.value)
    elif isinstance(q, LtQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.lt(tag_name, q.value)
    elif isinstance(q, LteQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.lte(tag_name, q.value)
    elif isinstance(q, LikeQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.like(tag_name, q.value)
    elif isinstance(q, InQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.in_(tag_name, q.values)
    elif isinstance(q, ExistQuery):
        tag_names = [
            TagName(k.lstrip("~")) for k in q.keys
        ]  # Ignore and remove '~' from each key
        return TagQuery.exist(tag_names)
    else:
        raise ValueError(f"Unknown query type: {type(q)}")
