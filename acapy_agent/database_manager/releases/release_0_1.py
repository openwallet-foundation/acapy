"""Module docstring."""

from acapy_agent.database_manager.databases.postgresql_normalized.handlers import (
    generic_handler as pg_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.handlers import (
    normalized_handler as pn_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom import (
    connection_metadata_custom_handler as pconn_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom import (
    cred_ex_v20_custom_handler as pcred_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.handlers.custom import (
    pres_ex_v20_custom_handler as ppres_handler,
)
from acapy_agent.database_manager.databases.postgresql_normalized.schema_context import (
    SchemaContext,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers import (
    generic_handler as sg_handler,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers import (
    normalized_handler as sn_handler,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom import (
    connection_metadata_custom_handler as sconn_handler,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom import (
    cred_ex_v20_custom_handler as scred_handler,
)
from acapy_agent.database_manager.databases.sqlite_normalized.handlers.custom import (
    pres_ex_v20_custom_handler as spres_handler,
)

from ..category_registry import load_schema

RELEASE = {
    "connection": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "connection",
                table_name="connection_v0_1",
                columns=load_schema("connection", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "connection",
                table_name="connection_v0_1",
                columns=load_schema("connection", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("connection", "0_1")["schemas"],
        "drop_schemas": load_schema("connection", "0_1")["drop_schemas"],
    },
    "oob_record": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "oob_record",
                table_name="oob_record_v0_1",
                columns=load_schema("oob_record", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "oob_record",
                table_name="oob_record_v0_1",
                columns=load_schema("oob_record", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("oob_record", "0_1")["schemas"],
        "drop_schemas": load_schema("oob_record", "0_1")["drop_schemas"],
    },
    "transaction": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "transaction",
                table_name="transaction_record_v0_1",
                columns=load_schema("transaction", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "transaction",
                table_name="transaction_record_v0_1",
                columns=load_schema("transaction", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("transaction", "0_1")["schemas"],
        "drop_schemas": load_schema("transaction", "0_1")["drop_schemas"],
    },
    "schema_sent": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "schema_sent",
                table_name="schema_sent_v0_1",
                columns=load_schema("schema_sent", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "schema_sent",
                table_name="schema_sent_v0_1",
                columns=load_schema("schema_sent", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("schema_sent", "0_1")["schemas"],
        "drop_schemas": load_schema("schema_sent", "0_1")["drop_schemas"],
    },
    "did": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "did", table_name="did_v0_1", columns=load_schema("did", "0_1")["columns"]
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "did",
                table_name="did_v0_1",
                columns=load_schema("did", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("did", "0_1")["schemas"],
        "drop_schemas": load_schema("did", "0_1")["drop_schemas"],
    },
    "cred_def_sent": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "cred_def_sent",
                table_name="cred_def_sent_v0_1",
                columns=load_schema("cred_def_sent", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "cred_def_sent",
                table_name="cred_def_sent_v0_1",
                columns=load_schema("cred_def_sent", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("cred_def_sent", "0_1")["schemas"],
        "drop_schemas": load_schema("cred_def_sent", "0_1")["drop_schemas"],
    },
    "credential_def": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "credential_def",
                table_name="credential_def_v0_1",
                columns=load_schema("credential_def", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "credential_def",
                table_name="credential_def_v0_1",
                columns=load_schema("credential_def", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("credential_def", "0_1")["schemas"],
        "drop_schemas": load_schema("credential_def", "0_1")["drop_schemas"],
    },
    "schema": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "schema",
                table_name="schema_v0_1",
                columns=load_schema("schema", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "schema",
                table_name="schema_v0_1",
                columns=load_schema("schema", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("schema", "0_1")["schemas"],
        "drop_schemas": load_schema("schema", "0_1")["drop_schemas"],
    },
    "revocation_reg_def": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "revocation_reg_def",
                table_name="revocation_reg_def_v0_1",
                columns=load_schema("revocation_reg_def", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "revocation_reg_def",
                table_name="revocation_reg_def_v0_1",
                columns=load_schema("revocation_reg_def", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("revocation_reg_def", "0_1")["schemas"],
        "drop_schemas": load_schema("revocation_reg_def", "0_1")["drop_schemas"],
    },
    "cred_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": scred_handler.CredExV20CustomHandler(
                "cred_ex_v20",
                table_name="cred_ex_v20_v0_1",
                columns=load_schema("cred_ex_v20", "0_1")["columns"],
            ),
            "postgresql": pcred_handler.CredExV20CustomHandler(
                "cred_ex_v20",
                table_name="cred_ex_v20_v0_1",
                columns=load_schema("cred_ex_v20", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("cred_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("cred_ex_v20", "0_1")["drop_schemas"],
    },
    "connection_invitation": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "connection_invitation",
                table_name="connection_invitation_v0_1",
                columns=load_schema("connection_invitation", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "connection_invitation",
                table_name="connection_invitation_v0_1",
                columns=load_schema("connection_invitation", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("connection_invitation", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_invitation", "0_1")["drop_schemas"],
    },
    "connection_metadata": {
        "version": "0_1",
        "handlers": {
            "sqlite": sconn_handler.ConnectionMetadataCustomHandler(
                "connection_metadata",
                table_name="connection_metadata_v0_1",
                columns=load_schema("connection_metadata", "0_1")["columns"],
            ),
            "postgresql": pconn_handler.ConnectionMetadataCustomHandler(
                "connection_metadata",
                table_name="connection_metadata_v0_1",
                columns=load_schema("connection_metadata", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("connection_metadata", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_metadata", "0_1")["drop_schemas"],
    },
    "revocation_list": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "revocation_list",
                table_name="revocation_list_v0_1",
                columns=load_schema("revocation_list", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "revocation_list",
                table_name="revocation_list_v0_1",
                columns=load_schema("revocation_list", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("revocation_list", "0_1")["schemas"],
        "drop_schemas": load_schema("revocation_list", "0_1")["drop_schemas"],
    },
    "connection_request": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "connection_request",
                table_name="connection_request_v0_1",
                columns=load_schema("connection_request", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "connection_request",
                table_name="connection_request_v0_1",
                columns=load_schema("connection_request", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("connection_request", "0_1")["schemas"],
        "drop_schemas": load_schema("connection_request", "0_1")["drop_schemas"],
    },
    "issuer_cred_rev": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "issuer_cred_rev",
                table_name="issuer_cred_rev_v0_1",
                columns=load_schema("issuer_cred_rev", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "issuer_cred_rev",
                table_name="issuer_cred_rev_v0_1",
                columns=load_schema("issuer_cred_rev", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("issuer_cred_rev", "0_1")["schemas"],
        "drop_schemas": load_schema("issuer_cred_rev", "0_1")["drop_schemas"],
    },
    "pres_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": spres_handler.PresExV20CustomHandler(
                "pres_ex_v20",
                table_name="pres_ex_v20_v0_1",
                columns=load_schema("pres_ex_v20", "0_1")["columns"],
            ),
            "postgresql": ppres_handler.PresExV20CustomHandler(
                "pres_ex_v20",
                table_name="pres_ex_v20_v0_1",
                columns=load_schema("pres_ex_v20", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("pres_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("pres_ex_v20", "0_1")["drop_schemas"],
    },
    "anoncreds_cred_ex_v20": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "anoncreds_cred_ex_v20",
                table_name="anoncreds_cred_ex_v20_v0_1",
                columns=load_schema("anoncreds_cred_ex_v20", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "anoncreds_cred_ex_v20",
                table_name="anoncreds_cred_ex_v20_v0_1",
                columns=load_schema("anoncreds_cred_ex_v20", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("anoncreds_cred_ex_v20", "0_1")["schemas"],
        "drop_schemas": load_schema("anoncreds_cred_ex_v20", "0_1")["drop_schemas"],
    },
    "did_key": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "did_key",
                table_name="did_key_v0_1",
                columns=load_schema("did_key", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "did_key",
                table_name="did_key_v0_1",
                columns=load_schema("did_key", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("did_key", "0_1")["schemas"],
        "drop_schemas": load_schema("did_key", "0_1")["drop_schemas"],
    },
    "did_doc": {
        "version": "0_1",
        "handlers": {
            "sqlite": sn_handler.NormalizedHandler(
                "did_doc",
                table_name="did_doc_v0_1",
                columns=load_schema("did_doc", "0_1")["columns"],
            ),
            "postgresql": pn_handler.NormalizedHandler(
                "did_doc",
                table_name="did_doc_v0_1",
                columns=load_schema("did_doc", "0_1")["columns"],
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("did_doc", "0_1")["schemas"],
        "drop_schemas": load_schema("did_doc", "0_1")["drop_schemas"],
    },
    "credential": {
        "version": "0_1",
        "handlers": {
            "sqlite": sg_handler.GenericHandler(
                "credential", tags_table_name="credential_record_v0_1"
            ),
            "postgresql": pg_handler.GenericHandler(
                "credential",
                tags_table_name="credential_record_v0_1",
                schema_context=SchemaContext(),
            ),
        },
        "schemas": load_schema("credential", "0_1")["schemas"],
        "drop_schemas": load_schema("credential", "0_1")["drop_schemas"],
    },
    "default": {
        "version": "0_1",
        "handlers": {
            "sqlite": sg_handler.GenericHandler("default", tags_table_name="items_tags"),
            "postgresql": pg_handler.GenericHandler(
                "default", tags_table_name="items_tags", schema_context=SchemaContext()
            ),
        },
        "schemas": None,
    },
}
