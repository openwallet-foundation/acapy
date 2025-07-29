from acapy_agent.database_manager.databases.sqlite_normalized.handlers.normalized_handler import NormalizedHandler as SqliteNormalizedHandler
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.generic_handler import GenericHandler as SqliteGenericHandler
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom.cred_ex_v20_custom_handler import CredExV20CustomHandler as SqliteCredExV20CustomHandler
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom.pres_ex_v20_custom_handler import PresExV20CustomHandler as SqlitePresExV20CustomHandler
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom.connection_metadata_custom_handler import ConnectionMetadataCustomHandler as SqliteConnectionMetadataCustomHandler
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.normalized_handler import NormalizedHandler as PostgresqlNormalizedHandler
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.generic_handler import GenericHandler as PostgresqlGenericHandler
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom.cred_ex_v20_custom_handler import CredExV20CustomHandler as PostgresqlCredExV20CustomHandler
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom.pres_ex_v20_custom_handler import PresExV20CustomHandler as PostgresqlPresExV20CustomHandler
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom.connection_metadata_custom_handler import ConnectionMetadataCustomHandler as PostgresqlConnectionMetadataCustomHandler
from acapy_agent.database_manager.databases.postgresql_normalized.schema_context import SchemaContext
from ..category_registry import load_schema

RELEASE = {
    "connection": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("connection", table_name="connection_v0_1", columns=load_schema("connection", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("connection", table_name="connection_v0_1", columns=load_schema("connection", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("connection", "0_1")["schemas"],
        "drop_schemas": load_schema("connection", "0_1")["drop_schemas"]
    },
    "oob_record": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("oob_record", table_name="oob_record_v0_1", columns=load_schema("oob_record", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("oob_record", table_name="oob_record_v0_1", columns=load_schema("oob_record", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("oob_record", "0_1")["schemas"],
        "drop_schemas": load_schema("oob_record", "0_1")["drop_schemas"]
    },
    "transaction": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("transaction", table_name="transaction_record_v0_1", columns=load_schema("transaction", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("transaction", table_name="transaction_record_v0_1", columns=load_schema("transaction", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("transaction", "0_1")["schemas"],
        "drop_schemas": load_schema("transaction", "0_1")["drop_schemas"]
    },
    "schema_sent": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("schema_sent", table_name="schema_sent_v0_1", columns=load_schema("schema_sent", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("schema_sent", table_name="schema_sent_v0_1", columns=load_schema("schema_sent", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("schema_sent", "0_1")["schemas"],
        "drop_schemas": load_schema("schema_sent", "0_1")["drop_schemas"]
    },
    "did": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("did", table_name="did_v0_1", columns=load_schema("did", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("did", table_name="did_v0_1", columns=load_schema("did", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("did", "0_1")["schemas"],
        "drop_schemas": load_schema("did", "0_1")["drop_schemas"]
    },
    "cred_def_sent": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("cred_def_sent", table_name="cred_def_sent_v0_1", columns=load_schema("cred_def_sent", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("cred_def_sent", table_name="cred_def_sent_v0_1", columns=load_schema("cred_def_sent", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("cred_def_sent", "0_1")["schemas"],
        "drop_schemas": load_schema("cred_def_sent", "0_1")["drop_schemas"]
    },
    "credential_def": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("credential_def", table_name="credential_def_v0_1", columns=load_schema("credential_def", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("credential_def", table_name="credential_def_v0_1", columns=load_schema("credential_def", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("credential_def", "0_1")["schemas"],
        "drop_schemas": load_schema("credential_def", "0_1")["drop_schemas"]
    },
    "schema": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("schema", table_name="schema_v0_1", columns=load_schema("schema", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("schema", table_name="schema_v0_1", columns=load_schema("schema", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("schema", "0_1")["schemas"],
        "drop_schemas": load_schema("schema", "0_1")["drop_schemas"]
    },
    "revocation_reg_def": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("revocation_reg_def", table_name="revocation_reg_def_v0_1", columns=load_schema("revocation_reg_def", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("revocation_reg_def", table_name="revocation_reg_def_v0_1", columns=load_schema("revocation_reg_def", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("revocation_reg_def", "0_1")["schemas"],
        "drop_schemas": load_schema("revocation_reg_def", "0_1")["drop_schemas"]
    },
    "cred_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteCredExV20CustomHandler("cred_ex_v20", table_name="cred_ex_v20_v0_1", columns=load_schema("cred_ex_v20", "0_1")["columns"]),
            "postgresql": PostgresqlCredExV20CustomHandler("cred_ex_v20", table_name="cred_ex_v20_v0_1", columns=load_schema("cred_ex_v20", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("cred_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("cred_ex_v20", "0_1")["drop_schemas"]
    },
    "connection_invitation": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("connection_invitation", table_name="connection_invitation_v0_1", columns=load_schema("connection_invitation", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("connection_invitation", table_name="connection_invitation_v0_1", columns=load_schema("connection_invitation", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("connection_invitation", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_invitation", "0_1")["drop_schemas"]
    },
    "connection_metadata": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteConnectionMetadataCustomHandler("connection_metadata", table_name="connection_metadata_v0_1", columns=load_schema("connection_metadata", "0_1")["columns"]),
            "postgresql": PostgresqlConnectionMetadataCustomHandler("connection_metadata", table_name="connection_metadata_v0_1", columns=load_schema("connection_metadata", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("connection_metadata", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_metadata", "0_1")["drop_schemas"]
    },
    "revocation_list": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("revocation_list", table_name="revocation_list_v0_1", columns=load_schema("revocation_list", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("revocation_list", table_name="revocation_list_v0_1", columns=load_schema("revocation_list", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("revocation_list", "0_1")["schemas"],
        "drop_schemas": load_schema("revocation_list", "0_1")["drop_schemas"]
    },
    "connection_request": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("connection_request", table_name="connection_request_v0_1", columns=load_schema("connection_request", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("connection_request", table_name="connection_request_v0_1", columns=load_schema("connection_request", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("connection_request", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_request", "0_1")["drop_schemas"]
    },
    "issuer_cred_rev": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("issuer_cred_rev", table_name="issuer_cred_rev_v0_1", columns=load_schema("issuer_cred_rev", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("issuer_cred_rev", table_name="issuer_cred_rev_v0_1", columns=load_schema("issuer_cred_rev", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("issuer_cred_rev", "0_1")["schemas"],
        "drop_schemas": load_schema("issuer_cred_rev", "0_1")["drop_schemas"]
    },
    "pres_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqlitePresExV20CustomHandler("pres_ex_v20", table_name="pres_ex_v20_v0_1", columns=load_schema("pres_ex_v20", "0_1")["columns"]),
            "postgresql": PostgresqlPresExV20CustomHandler("pres_ex_v20", table_name="pres_ex_v20_v0_1", columns=load_schema("pres_ex_v20", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("pres_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("pres_ex_v20", "0_1")["drop_schemas"]
    },
    "anoncreds_cred_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("anoncreds_cred_ex_v20", table_name="anoncreds_cred_ex_v20_v0_1", columns=load_schema("anoncreds_cred_ex_v20", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("anoncreds_cred_ex_v20", table_name="anoncreds_cred_ex_v20_v0_1", columns=load_schema("anoncreds_cred_ex_v20", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("anoncreds_cred_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("anoncreds_cred_ex_v20", "0_1")["drop_schemas"]
    },
    "did_key": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("did_key", table_name="did_key_v0_1", columns=load_schema("did_key", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("did_key", table_name="did_key_v0_1", columns=load_schema("did_key", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("did_key", "0_1")["schemas"],
        "drop_schemas": load_schema("did_key", "0_1")["drop_schemas"]
    },
    "did_doc": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteNormalizedHandler("did_doc", table_name="did_doc_v0_1", columns=load_schema("did_doc", "0_1")["columns"]),
            "postgresql": PostgresqlNormalizedHandler("did_doc", table_name="did_doc_v0_1", columns=load_schema("did_doc", "0_1")["columns"], schema_context=SchemaContext())
        },
        "schemas": load_schema("did_doc", "0_1")["schemas"],
        "drop_schemas": load_schema("did_doc", "0_1")["drop_schemas"]
    },
    "credential": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteGenericHandler("credential", tags_table_name="credential_record_v0_1"),
            "postgresql": PostgresqlGenericHandler("credential", tags_table_name="credential_record_v0_1", schema_context=SchemaContext())
        },
        "schemas": load_schema("credential", "0_1")["schemas"],
        "drop_schemas": load_schema("credential", "0_1")["drop_schemas"]
    },
    "default": {
        "version": "0_1",
        "handlers": {
            "sqlite": SqliteGenericHandler("default", tags_table_name="items_tags"),
            "postgresql": PostgresqlGenericHandler("default", tags_table_name="items_tags", schema_context=SchemaContext())
        },
        "schemas": None
    }
}
