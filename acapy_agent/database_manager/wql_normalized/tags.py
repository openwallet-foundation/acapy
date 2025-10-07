"""Module docstring."""

import json
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional, Tuple

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
    """Represents a tag name."""

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
        variant_handlers = {
            "Eq": self._handle_eq_variant,
            "Neq": self._handle_neq_variant,
            "Gt": self._handle_gt_variant,
            "Gte": self._handle_gte_variant,
            "Lt": self._handle_lt_variant,
            "Lte": self._handle_lte_variant,
            "Like": self._handle_like_variant,
            "In": self._handle_in_variant,
            "Exist": self._handle_exist_variant,
            "And": self._handle_and_variant,
            "Or": self._handle_or_variant,
            "Not": self._handle_not_variant,
        }

        handler = variant_handlers.get(self.variant)
        if handler:
            return handler()
        else:
            raise ValueError(f"Unknown query variant: {self.variant}")

    def _handle_eq_variant(self):
        """Handle Eq variant."""
        name, value = self.data
        return {name.to_string(): value}

    def _handle_neq_variant(self):
        """Handle Neq variant."""
        name, value = self.data
        return {name.to_string(): {"$neq": value}}

    def _handle_gt_variant(self):
        """Handle Gt variant."""
        name, value = self.data
        return {name.to_string(): {"$gt": value}}

    def _handle_gte_variant(self):
        """Handle Gte variant."""
        name, value = self.data
        return {name.to_string(): {"$gte": value}}

    def _handle_lt_variant(self):
        """Handle Lt variant."""
        name, value = self.data
        return {name.to_string(): {"$lt": value}}

    def _handle_lte_variant(self):
        """Handle Lte variant."""
        name, value = self.data
        return {name.to_string(): {"$lte": value}}

    def _handle_like_variant(self):
        """Handle Like variant."""
        name, value = self.data
        return {name.to_string(): {"$like": value}}

    def _handle_in_variant(self):
        """Handle In variant."""
        name, values = self.data
        return {name.to_string(): {"$in": values}}

    def _handle_exist_variant(self):
        """Handle Exist variant."""
        names = self.data
        return {"$exist": [name.to_string() for name in names]}

    def _handle_and_variant(self):
        """Handle And variant."""
        subqueries = self.data
        if not subqueries:
            return {}
        return {"$and": [sq.to_wql_dict() for sq in subqueries]}

    def _handle_or_variant(self):
        """Handle Or variant."""
        subqueries = self.data
        if not subqueries:
            return {}
        return {"$or": [sq.to_wql_dict() for sq in subqueries]}

    def _handle_not_variant(self):
        """Handle Not variant."""
        subquery = self.data
        return {"$not": subquery.to_wql_dict()}

    def to_wql_str(self):
        """Convert the TagQuery to a WQL JSON string."""
        return json.dumps(self.to_wql_dict())

    def to_sql(self, table_columns: Optional[set] = None) -> Tuple[str, list]:
        """Convert the TagQuery to an SQL condition and parameters for normalized tables.

        Args:
            table_columns (Optional[set]): Set of valid column names for validation.

        Returns:
            Tuple[str, list]: SQL condition string and list of parameters.

        Raises:
            ValueError: If an invalid column name is used or an unsupported
                query type is encountered.

        """
        if self.variant in ["Eq", "Neq", "Gt", "Gte", "Lt", "Lte", "Like"]:
            name, value = self.data
            column = name.to_string()
            if table_columns and column not in table_columns:
                raise ValueError(f"Invalid column name: {column}")
            op = {
                "Eq": "=",
                "Neq": "!=",
                "Gt": ">",
                "Gte": ">=",
                "Lt": "<",
                "Lte": "<=",
                "Like": "LIKE",
            }[self.variant]
            return f"{column} {op} ?", [value]
        elif self.variant == "In":
            name, values = self.data
            column = name.to_string()
            if table_columns and column not in table_columns:
                raise ValueError(f"Invalid column name: {column}")
            placeholders = ", ".join(["?" for _ in values])
            return f"{column} IN ({placeholders})", values
        elif self.variant == "Exist":
            names = self.data
            if len(names) != 1:
                raise ValueError("Exist query must have exactly one tag name")
            column = names[0].to_string()
            if table_columns and column not in table_columns:
                raise ValueError(f"Invalid column name: {column}")
            return f"{column} IS NOT NULL", []
        elif self.variant in ["And", "Or"]:
            subqueries = self.data
            if not subqueries:
                return "1=1" if self.variant == "And" else "1=0", []
            sub_sqls = [sq.to_sql(table_columns) for sq in subqueries]
            conditions = [s[0] for s in sub_sqls]
            params = [p for s in sub_sqls for p in s[1]]
            conjunction = " AND " if self.variant == "And" else " OR "
            return "(" + conjunction.join(conditions) + ")", params
        elif self.variant == "Not":
            subquery = self.data
            sub_sql, sub_params = subquery.to_sql(table_columns)
            return f"NOT ({sub_sql})", sub_params
        else:
            raise ValueError(f"Unsupported query variant: {self.variant}")


class TagQueryEncoder(ABC):
    """Class description."""

    @abstractmethod
    def encode_name(self, name: TagName) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_value(self, value: str) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_op_clause(
        self, op: CompareOp, enc_name: str, enc_value: str, negate: bool
    ) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_in_clause(self, enc_name: str, enc_values: List[str], negate: bool) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_exist_clause(self, enc_name: str, negate: bool) -> str:
        """Perform the action."""
        pass

    @abstractmethod
    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        """Perform the action."""
        pass

    def encode_query(self, query: TagQuery, negate: bool = False) -> str:
        """Perform the action."""
        if query.variant == "Eq":
            return self.encode_op(CompareOp.Eq, *query.data, negate)
        elif query.variant == "Neq":
            return self.encode_op(CompareOp.Neq, *query.data, negate)
        elif query.variant == "Gt":
            return self.encode_op(CompareOp.Gt, *query.data, negate)
        elif query.variant == "Gte":
            return self.encode_op(CompareOp.Gte, *query.data, negate)
        elif query.variant == "Lt":
            return self.encode_op(CompareOp.Lt, *query.data, negate)
        elif query.variant == "Lte":
            return self.encode_op(CompareOp.Lte, *query.data, negate)
        elif query.variant == "Like":
            return self.encode_op(CompareOp.Like, *query.data, negate)
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
