from acapy_agent.database_manager.wql_normalized.encoders.postgres_encoder import (
    PostgresTagEncoder,
)
from acapy_agent.database_manager.wql_normalized.tags import TagName, TagQuery


def passthrough(x: str) -> str:
    return x


def test_encode_eq_top_level_normalized():
    enc = PostgresTagEncoder(passthrough, passthrough, normalized=True, table_alias="t")
    q = TagQuery.eq(TagName("schema_id"), "s1")
    sql, args = enc.encode_query(q)
    assert sql == "t.schema_id = %s"
    assert args == ["s1"]


def test_encode_not_exist_non_normalized():
    enc = PostgresTagEncoder(passthrough, passthrough, normalized=False)
    q = TagQuery.not_(TagQuery.exist([TagName("rev_reg_id")]))
    sql, args = enc.encode_query(q)
    assert "NOT IN" in sql or "IS" in sql
    assert isinstance(args, list)


def test_encode_in_and_or_mix():
    enc = PostgresTagEncoder(passthrough, passthrough, normalized=True, table_alias="t")
    sub1 = TagQuery.in_(TagName("issuer_did"), ["did:indy:123", "did:indy:456"])
    sub2 = TagQuery.like(TagName("schema_name"), "%email%")
    q = TagQuery.and_([sub1, TagQuery.or_([sub2])])
    sql, args = enc.encode_query(q)
    assert sql.startswith("(") and sql.endswith(")")
    assert args == ["did:indy:123", "did:indy:456", "%email%"]
