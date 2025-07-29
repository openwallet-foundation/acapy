from typing import List
from ..tags import TagQueryEncoder, TagName, CompareOp, ConjunctionOp, TagQuery
import logging

LOGGER = logging.getLogger(__name__)

class SqliteTagEncoder(TagQueryEncoder):
    """
    Encoder for generating SQLite-compatible SQL queries from TagQuery objects.
    Uses '?' placeholders for parameters.
    Supports both normalized and non-normalized modes with a configurable tags table for non-normalized mode.
    """

    def __init__(self, enc_name, enc_value, normalized: bool = False, table_alias: str = 't', tags_table: str = 'items_tags'):
        """
        Initialize the encoder with functions to encode tag names and values, a mode flag,
        an optional table alias, and an optional tags table name for non-normalized mode.

        Args:
            enc_name (callable): Function to encode tag names (str -> str).
            enc_value (callable): Function to encode tag values (str -> str).
            normalized (bool): Flag to indicate if the encoder should use normalized mode (default: False).
            table_alias (str): Table alias to use in normalized mode (default: 't').
            tags_table (str): Name of the tags table for non-normalized mode (default: 'items_tags').
        """
        self.enc_name = enc_name
        self.enc_value = enc_value
        self.normalized = normalized
        self.table_alias = table_alias if normalized else None
        self.tags_table = tags_table
        self.arguments = []  # List to store parameter values
        #LOGGER.debug("Initialized SqliteTagEncoder with normalized=%s, table_alias=%s, tags_table=%s",
        #             normalized, table_alias, tags_table)

    def encode_name(self, name: TagName) -> str:
        """Encode the tag name using the provided enc_name function."""
        operation_name = "encode_name"
        result = self.enc_name(name.value)
        encoded_name = result if isinstance(result, str) else str(result)
        #LOGGER.debug("[%s] Encoded name %s to %s", operation_name, name.value, encoded_name)
        return encoded_name

    def encode_value(self, value: str) -> str:
        """Encode the tag value using the provided enc_value function."""
        operation_name = "encode_value"
        result = self.enc_value(value)
        encoded_value = result if isinstance(result, str) else str(result)
        #LOGGER.debug("[%s] Encoded value %s to %s", operation_name, value, encoded_value)
        return encoded_value

    def encode_query(self, query: TagQuery, negate: bool = False, top_level: bool = True) -> str:
        """Encode the query and reset arguments list only at top level."""
        operation_name = "encode_query"
        #LOGGER.debug("[%s] Starting with query=%s, negate=%s, top_level=%s, tags_table=%s",
         #            operation_name, query, negate, top_level, self.tags_table)
        
        if top_level:
            self.arguments = []  # Reset arguments only for top-level query
        
        try:
            if query.variant == "Not":
                if query.data.variant == "Exist":
                    return self.encode_exist(query.data.data, True)
                elif query.data.variant == "In":
                    return self.encode_in(*query.data.data, True)
                elif not self.normalized and query.data.variant in ["Eq", "Neq", "Gt", "Gte", "Lt", "Lte", "Like"]:
                    return self.encode_op(getattr(CompareOp, query.data.variant), *query.data.data, True)
                subquery = self.encode_query(query.data, False, top_level=False)
                if query.data.variant in ["And", "Or"]:
                    #LOGGER.debug("[%s] Encoding NOT for %s subquery: %s", operation_name, query.data.variant, subquery)
                    return f"NOT {subquery}"
                return f"NOT ({subquery})"
            
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
            else:
                LOGGER.error("[%s] Unknown query variant: %s", operation_name, query.variant)
                raise ValueError(f"Unknown query variant: {query.variant}")
        except Exception as e:
            LOGGER.error("[%s] Failed: %s", operation_name, str(e))
            raise

    def encode_op_clause(self, op: CompareOp, enc_name: str, enc_value: str, negate: bool) -> str:
        """
        Encode a comparison operation clause for SQLite.

        In normalized mode, generates direct column comparisons (e.g., "t.column = ?").
        In non-normalized mode, generates subqueries using the configured tags table (e.g., "i.id IN (SELECT item_id FROM tags_table ...)").
        """
        operation_name = "encode_op_clause"
        #LOGGER.debug("[%s] Encoding op=%s, enc_name=%s, enc_value=%s, negate=%s, normalized=%s, tags_table=%s",
        #             operation_name, op, enc_name, enc_value, negate, self.normalized, self.tags_table)
        
        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            sql_op = op.as_sql_str()
            if negate:
                negate_map = {
                    "=": "!=",
                    "!=": "=",
                    ">": "<=",
                    ">=": "<",
                    "<": ">=",
                    "<=": ">",
                    "LIKE": "NOT LIKE"
                }
                sql_op = negate_map.get(sql_op, sql_op)
            self.arguments.append(enc_value)
            sql_clause = f"{column} {sql_op} ?"
            #LOGGER.debug("[%s] Generated normalized clause: %s", operation_name, sql_clause)
            return sql_clause
        else:
            self.arguments.append(enc_name)
            self.arguments.append(enc_value)
            subquery_op = "NOT IN" if negate else "IN"
            sql_clause = f"i.id {subquery_op} (SELECT item_id FROM {self.tags_table} WHERE name = ? AND value {op.as_sql_str()} ?)"
            #LOGGER.debug("[%s] Generated non-normalized clause: %s", operation_name, sql_clause)
            return sql_clause

    def encode_in_clause(self, enc_name: str, enc_values: List[str], negate: bool) -> str:
        """
        Encode an 'IN' clause for multiple values in SQLite.
        """
        operation_name = "encode_in_clause"
        #LOGGER.debug("[%s] Encoding enc_name=%s, enc_values=%s, negate=%s, normalized=%s, tags_table=%s",
        #            operation_name, enc_name, enc_values, negate, self.normalized, self.tags_table)
        
        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            placeholders = ', '.join(['?' for _ in enc_values])
            self.arguments.extend(enc_values)
            sql_clause = f"{column} {'NOT IN' if negate else 'IN'} ({placeholders})"
            #LOGGER.debug("[%s] Generated normalized clause: %s", operation_name, sql_clause)
            return sql_clause
        else:
            self.arguments.append(enc_name)
            self.arguments.extend(enc_values)
            value_placeholders = ', '.join(['?' for _ in enc_values])
            sql_clause = f"i.id IN (SELECT item_id FROM {self.tags_table} WHERE name = ? AND value {'NOT IN' if negate else 'IN'} ({value_placeholders}))"
           # LOGGER.debug("[%s] Generated non-normalized clause: %s", operation_name, sql_clause)
            return sql_clause

    def encode_exist_clause(self, enc_name: str, negate: bool) -> str:
        """
        Encode an 'EXISTS' clause for tag or column existence in SQLite.
        """
        operation_name = "encode_exist_clause"
        #LOGGER.debug("[%s] Encoding enc_name=%s, negate=%s, normalized=%s, tags_table=%s",
         #            operation_name, enc_name, negate, self.normalized, self.tags_table)
        
        if self.normalized:
            column = f"{self.table_alias}.{enc_name}" if self.table_alias else enc_name
            sql_clause = f"{column} {'IS NULL' if negate else 'IS NOT NULL'}"
            LOGGER.debug("[%s] Generated normalized clause: %s", operation_name, sql_clause)
            return sql_clause
        else:
            self.arguments.append(enc_name)
            subquery_op = "NOT IN" if negate else "IN"
            sql_clause = f"i.id {subquery_op} (SELECT item_id FROM {self.tags_table} WHERE name = ?)"
            #LOGGER.debug("[%s] Generated non-normalized clause: %s", operation_name, sql_clause)
            return sql_clause

    def encode_conj_clause(self, op: ConjunctionOp, clauses: List[str]) -> str:
        """
        Encode a conjunction clause (AND/OR) for SQLite.
        """
        operation_name = "encode_conj_clause"
        #LOGGER.debug("[%s] Encoding op=%s, clauses=%s", operation_name, op, clauses)
        
        if not clauses:
            if op == ConjunctionOp.Or:
                return "1=0"  # False for empty OR
            return "1=1"  # True for empty AND
        sql_clause = "(" + op.as_sql_str().join(clauses) + ")"
        #LOGGER.debug("[%s] Generated clause: %s", operation_name, sql_clause)
        return sql_clause

    def encode_op(self, op: CompareOp, name: TagName, value: str, negate: bool):
        operation_name = "encode_op"
        #LOGGER.debug("[%s] Encoding op=%s, name=%s, value=%s, negate=%s", operation_name, op, name, value, negate)
        enc_name = self.encode_name(name)
        enc_value = self.encode_value(value)
        return self.encode_op_clause(op, enc_name, enc_value, negate)

    def encode_in(self, name: TagName, values: List[str], negate: bool):
        operation_name = "encode_in"
        #LOGGER.debug("[%s] Encoding name=%s, values=%s, negate=%s", operation_name, name, values, negate)
        enc_name = self.encode_name(name)
        enc_values = [self.encode_value(v) for v in values]
        return self.encode_in_clause(enc_name, enc_values, negate)

    def encode_exist(self, names: List[TagName], negate: bool):
        operation_name = "encode_exist"
        #LOGGER.debug("[%s] Encoding names=%s, negate=%s", operation_name, names, negate)
        if not names:
            #LOGGER.debug("[%s] No names provided, returning None", operation_name)
            return None
        elif len(names) == 1:
            enc_name = self.encode_name(names[0])
            return self.encode_exist_clause(enc_name, negate)
        else:
            clauses = [self.encode_exist([name], negate) for name in names]
            return self.encode_conj_clause(ConjunctionOp.And, [c for c in clauses if c])

    def encode_conj(self, op: ConjunctionOp, subqueries: List[TagQuery], negate: bool):
        operation_name = "encode_conj"
        #LOGGER.debug("[%s] Encoding op=%s, subqueries=%s, negate=%s", operation_name, op, subqueries, negate)
        op = op.negate() if negate else op
        clauses = []
        for q in subqueries:
            clause = self.encode_query(q, negate, top_level=False)
            if clause is not None:
                clauses.append(clause)
        return self.encode_conj_clause(op, clauses)