"""Module docstring."""

from typing import List, Dict, Any
from ..tags import TagQueryEncoder, TagName, CompareOp, ConjunctionOp


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
        """Encode a comparison operation clause."""
        if op == CompareOp.Eq:
            if negate:
                return {enc_name: {"$ne": enc_value}}
            else:
                return {enc_name: enc_value}  # Use shorthand for equality
        elif op == CompareOp.Neq:
            if negate:
                return {enc_name: enc_value}  # Negating "$ne" becomes equality
            else:
                return {enc_name: {"$ne": enc_value}}
        elif op == CompareOp.Like:
            pattern = enc_value
            if negate:
                return {enc_name: {"$not": {"$regex": pattern}}}
            else:
                return {enc_name: {"$regex": pattern}}
        else:
            # Handle other comparison operations
            mongo_op = {
                CompareOp.Gt: "$gt",
                CompareOp.Gte: "$gte",
                CompareOp.Lt: "$lt",
                CompareOp.Lte: "$lte",
            }.get(op)
            if mongo_op is None:
                raise ValueError(f"Unsupported operation: {op}")
            if negate:
                # Negate the operation using "$not"
                return {enc_name: {"$not": {mongo_op: enc_value}}}
            else:
                return {enc_name: {mongo_op: enc_value}}

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
