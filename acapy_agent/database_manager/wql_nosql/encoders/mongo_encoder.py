"""Module docstring."""

from typing import Any, Dict, List

from ..tags import CompareOp, ConjunctionOp, TagName, TagQueryEncoder


class MongoTagEncoder(TagQueryEncoder):
    """MongoDB query encoder for tag-based queries."""

    def __init__(self, enc_name, enc_value):
        """Initialize the MongoTagEncoder with encoding functions."""
        self.enc_name = enc_name
        self.enc_value = enc_value
        self.query = {}

    def encode_name(self, name: TagName) -> str:
        """Encode a tag name using the provided encoding function."""
        return self.enc_name(name.value)

    def encode_value(self, value: str) -> Any:
        """Encode a tag value using the provided encoding function."""
        return self.enc_value(value)

    def encode_op_clause(
        self, op: CompareOp, enc_name: str, enc_value: Any, negate: bool
    ) -> Dict:
        """Encode a comparison operation clause with low branching."""

        # Direct handlers for equality and like
        def handle_eq(name: str, value: Any, not_: bool) -> Dict:
            return {name: {"$ne": value}} if not_ else {name: value}

        def handle_neq(name: str, value: Any, not_: bool) -> Dict:
            return {name: value} if not_ else {name: {"$ne": value}}

        def handle_like(name: str, value: Any, not_: bool) -> Dict:
            regex_clause = {"$regex": value}
            return {name: {"$not": regex_clause}} if not_ else {name: regex_clause}

        direct_dispatch = {
            CompareOp.Eq: handle_eq,
            CompareOp.Neq: handle_neq,
            CompareOp.Like: handle_like,
        }

        if op in direct_dispatch:
            return direct_dispatch[op](enc_name, enc_value, negate)

        # Range-like ops share the same shape
        range_op_map = {
            CompareOp.Gt: "$gt",
            CompareOp.Gte: "$gte",
            CompareOp.Lt: "$lt",
            CompareOp.Lte: "$lte",
        }
        mongo_op = range_op_map.get(op)
        if not mongo_op:
            raise ValueError(f"Unsupported operation: {op}")
        clause = {mongo_op: enc_value}
        return {enc_name: {"$not": clause}} if negate else {enc_name: clause}

    def encode_in_clause(
        self, enc_name: str, enc_values: List[Any], negate: bool
    ) -> Dict:
        """Encode an IN clause for multiple values."""
        if negate:
            return {enc_name: {"$nin": enc_values}}
        else:
            return {enc_name: {"$in": enc_values}}

    def encode_exist_clause(self, enc_name: str, negate: bool) -> Dict:
        """Encode an EXISTS clause."""
        exists_value = not negate
        return {enc_name: {"$exists": exists_value}}

    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[Dict]) -> Dict:
        """Encode a conjunction (AND/OR) clause."""
        if not clauses:
            if op == ConjunctionOp.Or:
                return {"$or": []}
            return {}
        mongo_op = "$and" if op == ConjunctionOp.And else "$or"
        return {mongo_op: clauses}
