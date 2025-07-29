import json
from enum import Enum
from typing import List, Union
from abc import ABC, abstractmethod
from .query import AndQuery, OrQuery, NotQuery, EqQuery, NeqQuery, GtQuery, GteQuery, LtQuery, LteQuery, LikeQuery, InQuery, ExistQuery

class TagName:
    def __init__(self, value):
        self.value = value

    def to_string(self):
        return self.value

    def __eq__(self, other):
        return self.value == other.value

    def __repr__(self):
        return f"TagName(value='{self.value}')"    


class CompareOp(Enum):
    Eq = "="
    Neq = "!="
    Gt = ">"
    Gte = ">="
    Lt = "<"
    Lte = "<="
    Like = "LIKE"

    def as_sql_str(self):
        return self.value

    def as_sql_str_for_prefix(self):
        if self in [CompareOp.Eq, CompareOp.Neq, CompareOp.Gt, CompareOp.Gte, CompareOp.Lt, CompareOp.Lte]:
            return self.value
        return None

class ConjunctionOp(Enum):
    And = " AND "
    Or = " OR "

    def as_sql_str(self):
        return self.value

    def negate(self):
        if self == ConjunctionOp.And:
            return ConjunctionOp.Or
        elif self == ConjunctionOp.Or:
            return ConjunctionOp.And

class TagQuery:
    def __init__(self, variant: str, data: Union['TagQuery', List['TagQuery'], TagName, str, List[str]]):
        self.variant = variant
        self.data = data

    def __repr__(self):
        if isinstance(self.data, list):
            data_repr = [repr(d) for d in self.data]
            data_str = '[' + ', '.join(data_repr) + ']'
        elif isinstance(self.data, (TagQuery, TagName)):
            data_str = repr(self.data)
        else:
            data_str = f"'{self.data}'"
        return f"TagQuery(variant='{self.variant}', data={data_str})"

    @staticmethod
    def Eq(name: TagName, value: str):
        return TagQuery("Eq", (name, value))

    @staticmethod
    def Neq(name: TagName, value: str):
        return TagQuery("Neq", (name, value))

    @staticmethod
    def Gt(name: TagName, value: str):
        return TagQuery("Gt", (name, value))

    @staticmethod
    def Gte(name: TagName, value: str):
        return TagQuery("Gte", (name, value))

    @staticmethod
    def Lt(name: TagName, value: str):
        return TagQuery("Lt", (name, value))

    @staticmethod
    def Lte(name: TagName, value: str):
        return TagQuery("Lte", (name, value))

    @staticmethod
    def Like(name: TagName, value: str):
        return TagQuery("Like", (name, value))

    @staticmethod
    def In(name: TagName, values: List[str]):
        return TagQuery("In", (name, values))

    @staticmethod
    def Exist(names: List[TagName]):
        return TagQuery("Exist", names)

    @staticmethod
    def And(subqueries: List['TagQuery']):
        return TagQuery("And", subqueries)

    @staticmethod
    def Or(subqueries: List['TagQuery']):
        return TagQuery("Or", subqueries)

    @staticmethod
    def Not(subquery: 'TagQuery'):
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
    @abstractmethod
    def encode_name(self, name: TagName) -> bytes:
        pass

    @abstractmethod
    def encode_value(self, value: str) -> bytes:
        pass

    @abstractmethod
    def encode_op_clause(self, op: CompareOp, enc_name: bytes, enc_value: bytes, negate: bool) -> str:
        pass

    @abstractmethod
    def encode_in_clause(self, enc_name: bytes, enc_values: List[bytes], negate: bool) -> str:
        pass

    @abstractmethod
    def encode_exist_clause(self, enc_name: bytes, negate: bool) -> str:
        pass

    @abstractmethod
    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        pass

    def encode_query(self, query: TagQuery, negate: bool = False) -> str:
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
        enc_name = self.encode_name(name)
        enc_value = self.encode_value(value)
        return self.encode_op_clause(op, enc_name, enc_value, negate)


    def encode_in(self, name: TagName, values: List[str], negate: bool):
        enc_name = self.encode_name(name)
        enc_values = [self.encode_value(v) for v in values]
        return self.encode_in_clause(enc_name, enc_values, negate)


    def encode_exist(self, names: List[TagName], negate: bool):
        if not names:
            return None
        elif len(names) == 1:
            enc_name = self.encode_name(names[0])
            return self.encode_exist_clause(enc_name, negate)
        else:
            clauses = [self.encode_exist([name], negate) for name in names]
            return self.encode_conj_clause(ConjunctionOp.And, [c for c in clauses if c])
    
    
    def encode_conj(self, op: ConjunctionOp, subqueries: List[TagQuery], negate: bool):
        op = op.negate() if negate else op
        clauses = []
        for q in subqueries:
            clause = self.encode_query(q, negate)
            if clause is not None:
                clauses.append(clause)
        return self.encode_conj_clause(op, clauses)
    

def query_to_tagquery(q):
    """
    Convert a Query object from query.py to a TagQuery object from tags.py.
    Strips '~' from keys as it is no longer used to determine tag type.
    NOTE: this is for backward competbiltiy as the caller will continetue to
    provide the ~ character for plaintext.
    """
    if isinstance(q, AndQuery):
        return TagQuery.And([query_to_tagquery(sq) for sq in q.subqueries])
    elif isinstance(q, OrQuery):
        return TagQuery.Or([query_to_tagquery(sq) for sq in q.subqueries])
    elif isinstance(q, NotQuery):
        return TagQuery.Not(query_to_tagquery(q.subquery))
    elif isinstance(q, EqQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Eq(tag_name, q.value)
    elif isinstance(q, NeqQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Neq(tag_name, q.value)
    elif isinstance(q, GtQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Gt(tag_name, q.value)
    elif isinstance(q, GteQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Gte(tag_name, q.value)
    elif isinstance(q, LtQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Lt(tag_name, q.value)
    elif isinstance(q, LteQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Lte(tag_name, q.value)
    elif isinstance(q, LikeQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.Like(tag_name, q.value)
    elif isinstance(q, InQuery):
        key = q.key.lstrip("~")  # Ignore and remove '~' character from the key
        tag_name = TagName(key)
        return TagQuery.In(tag_name, q.values)
    elif isinstance(q, ExistQuery):
        tag_names = [TagName(k.lstrip("~")) for k in q.keys]  # Ignore and remove '~' from each key
        return TagQuery.Exist(tag_names)
    else:
        raise ValueError(f"Unknown query type: {type(q)}")