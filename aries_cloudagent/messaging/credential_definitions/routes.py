"""Credential definition admin routes."""

import json


from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields
from ...anoncreds.issuer import AnonCredsIssuer
from ...anoncreds.registry import AnonCredsRegistry

from ...wallet.base import BaseWallet

from ...admin.request_context import AdminRequestContext


from ...indy.models.cred_def import CredentialDefinitionSchema

from ...ledger.error import BadLedgerRequestError


from ...protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ...protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecordSchema,
)
from ...protocols.endorse_transaction.v1_0.util import (
    get_endorser_connection_id,
)


from ...storage.error import StorageError

from ..models.openapi import OpenAPISchema
from ..valid import INDY_CRED_DEF_ID, INDY_REV_REG_SIZE, INDY_SCHEMA_ID


from .util import (
    CredDefQueryStringSchema,
    notify_cred_def_event,
)


from ..valid import UUIDFour


class CredentialDefinitionSendRequestSchema(OpenAPISchema):
    """Request schema for schema send request."""

    schema_id = fields.Str(description="Schema identifier", **INDY_SCHEMA_ID)
    support_revocation = fields.Boolean(
        required=False, description="Revocation supported flag"
    )
    revocation_registry_size = fields.Int(
        description="Revocation registry size",
        required=False,
        strict=True,
        **INDY_REV_REG_SIZE,
    )
    tag = fields.Str(
        required=False,
        description="Credential definition identifier tag",
        default="default",
        example="default",
    )


class CredentialDefinitionSendResultSchema(OpenAPISchema):
    """Result schema content for schema send request with auto-endorse."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )


class TxnOrCredentialDefinitionSendResultSchema(OpenAPISchema):
    """Result schema for credential definition send request."""

    sent = fields.Nested(
        CredentialDefinitionSendResultSchema(),
        required=False,
        definition="Content sent",
    )
    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="Credential definition transaction to endorse",
    )


class CredentialDefinitionGetResultSchema(OpenAPISchema):
    """Result schema for schema get request."""

    credential_definition = fields.Nested(CredentialDefinitionSchema)


class CredentialDefinitionsCreatedResultSchema(OpenAPISchema):
    """Result schema for cred-defs-created request."""

    credential_definition_ids = fields.List(
        fields.Str(description="Credential definition identifiers", **INDY_CRED_DEF_ID)
    )


class CredDefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )


class CreateCredDefTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        description="Create Transaction For Endorser's signature",
        required=False,
    )


class CredDefConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=False, example=UUIDFour.EXAMPLE
    )


@docs(
    tags=["credential-definition"],
    summary="Sends a credential definition to the ledger",
)
@request_schema(CredentialDefinitionSendRequestSchema())
@querystring_schema(CreateCredDefTxnForEndorserOptionSchema())
@querystring_schema(CredDefConnIdMatchInfoSchema())
@response_schema(TxnOrCredentialDefinitionSendResultSchema(), 200, description="")
async def credential_definitions_send_credential_definition(request: web.BaseRequest):
    """
    Request handler for sending a credential definition to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition identifier

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    create_transaction_for_endorser = json.loads(
        request.query.get("create_transaction_for_endorser", "false")
    )
    connection_id = request.query.get("conn_id")

    body = await request.json()

    schema_id = body.get("schema_id")
    support_revocation = bool(body.get("support_revocation"))
    tag = body.get("tag")
    rev_reg_size = body.get("revocation_registry_size")

    my_public_info = None
    async with profile.session() as session:
        wallet = session.inject(BaseWallet)
        my_public_info = await wallet.get_public_did()
    if not my_public_info:
        raise BadLedgerRequestError(
            "Cannot publish credential definition without a public DID"
        )

    body = await request.json()
    issuer_id = my_public_info.did
    schema_id = body.get("schema_id")
    tag = body.get("tag")
    options = {}
    if support_revocation:
        options["support_revocation"] = True
        options["revocation_registry_size"] = rev_reg_size
    if create_transaction_for_endorser:
        endorser_connection_id = await get_endorser_connection_id(context.profile)
        if not endorser_connection_id:
            raise web.HTTPBadRequest(reason="No endorser connection found")

        options["endorser_connection_id"] = endorser_connection_id

    cred_def = body.get("credential_definition")

    issuer = AnonCredsIssuer(context.profile)
    result = await issuer.create_and_register_credential_definition(
        issuer_id,
        schema_id,
        tag,
        options=options,
    )

    cred_def_id = result.credential_definition_state.credential_definition_id
    novel = False  # no idea how to deterimine what to put here...
    meta_data = {
        "context": {
            "schema_id": schema_id,
            "cred_def_id": cred_def_id,
            "issuer_did": issuer_id,
            "support_revocation": support_revocation,
            "novel": novel,
            "tag": tag,
            "rev_reg_size": rev_reg_size,
        },
        "processing": {
            "create_pending_rev_reg": True,
        },
    }

    if not create_transaction_for_endorser:
        # Notify event
        meta_data["processing"]["auto_create_rev_reg"] = True
        await notify_cred_def_event(context.profile, cred_def_id, meta_data)

        return web.json_response(
            {
                "sent": {"credential_definition_id": cred_def_id},
                "credential_definition_id": cred_def_id,
            }
        )
    else:
        meta_data["processing"]["auto_create_rev_reg"] = context.settings.get_value(
            "endorser.auto_create_rev_reg"
        )

        transaction_mgr = TransactionManager(context.profile)
        try:
            transaction = await transaction_mgr.create_record(
                messages_attach=cred_def["signed_txn"],
                connection_id=connection_id,
                meta_data=meta_data,
            )
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

        # if auto-request, send the request to the endorser
        if context.settings.get_value("endorser.auto_request"):
            try:
                transaction, transaction_request = await transaction_mgr.create_request(
                    transaction=transaction,
                    # TODO see if we need to parameterize these params
                    # expires_time=expires_time,
                    # endorser_write_txn=endorser_write_txn,
                )
            except (StorageError, TransactionManagerError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

            await outbound_handler(
                transaction_request, connection_id=endorser_connection_id
            )

        return web.json_response(
            {
                "sent": {"credential_definition_id": cred_def_id},
                "txn": transaction.serialize(),
            }
        )


@docs(
    tags=["credential-definition"],
    summary="Search for matching credential definitions that agent originated",
)
@querystring_schema(CredDefQueryStringSchema())
@response_schema(CredentialDefinitionsCreatedResultSchema(), 200, description="")
async def credential_definitions_created(request: web.BaseRequest):
    """
    Request handler for retrieving credential definitions that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        The identifiers of matching credential definitions.

    """
    context: AdminRequestContext = request["context"]
    issuer = AnonCredsIssuer(context.profile)

    # can no longer search/filter by cred def id
    cred_def_ids = await issuer.get_created_credential_definitions(
        issuer_id=request.query.get("issuer_did"),
        schema_issuer_id=request.query.get("schema_issuer_did"),
        schema_id=request.query.get("schema_id"),
        schema_name=request.query.get("schema_name"),
        schema_version=request.query.get("schema_version"),
    )

    return web.json_response({"credential_definition_ids": cred_def_ids})


@docs(
    tags=["credential-definition"],
    summary="Gets a credential definition from the ledger",
)
@match_info_schema(CredDefIdMatchInfoSchema())
@response_schema(CredentialDefinitionGetResultSchema(), 200, description="")
async def credential_definitions_get_credential_definition(request: web.BaseRequest):
    """
    Request handler for getting a credential definition from the ledger.

    Args:
        request: aiohttp request object

    Returns:
        The credential definition details.

    """
    context: AdminRequestContext = request["context"]
    cred_def_id = request.match_info["cred_def_id"]

    anon_creds_registry = context.inject(AnonCredsRegistry)
    result = await anon_creds_registry.get_credential_definition(
        context.profile, cred_def_id
    )

    anoncreds_cred_def = {
        "ident": cred_def_id,
        "schemaId": result.credential_definition.schema_id,
        "typ": result.credential_definition.type,
        "tag": result.credential_definition.tag,
        "value": result.credential_definition.value.serialize(),
    }

    return web.json_response({"credential_definition": anoncreds_cred_def})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post(
                "/credential-definitions",
                credential_definitions_send_credential_definition,
            ),
            web.get(
                "/credential-definitions/created",
                credential_definitions_created,
                allow_head=False,
            ),
            web.get(
                "/credential-definitions/{cred_def_id}",
                credential_definitions_get_credential_definition,
                allow_head=False,
            ),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "credential-definition",
            "description": "Credential definition operations",
            "externalDocs": {
                "description": "Specification",
                "url": (
                    "https://github.com/hyperledger/indy-node/blob/master/"
                    "design/anoncreds.md#cred_def"
                ),
            },
        }
    )
