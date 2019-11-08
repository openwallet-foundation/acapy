"""Credential exchange admin routes."""

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import fields, Schema

from ....connections.models.connection_record import ConnectionRecord
from ....holder.base import BaseHolder
from ....messaging.credential_definitions.util import CRED_DEF_TAGS
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    UUIDFour,
)
from ....storage.error import StorageNotFoundError

from ...problem_report.message import ProblemReport

from .manager import CredentialManager
from .messages.credential_proposal import CredentialProposal
from .messages.inner.credential_preview import (
    CredentialPreview,
    CredentialPreviewSchema,
)
from .models.credential_exchange import (
    V10CredentialExchange,
    V10CredentialExchangeSchema,
)


class V10AttributeMimeTypesResultSchema(Schema):
    """Result schema for credential attribute MIME types by credential definition."""


class V10CredentialExchangeListResultSchema(Schema):
    """Result schema for Aries#0036 v1.0 credential exchange query."""

    results = fields.List(
        fields.Nested(V10CredentialExchangeSchema),
        description="Aries#0036 v1.0 credential exchange records",
    )


class V10CredentialProposalRequestSchema(Schema):
    """Request schema for sending credential proposal admin message."""

    connection_id = fields.UUID(
        description="Connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )
    schema_id = fields.Str(
        description="Schema identifier",
        required=False,
        **INDY_SCHEMA_ID,
    )
    schema_issuer_did = fields.Str(
        description="Schema issuer DID",
        required=False,
        **INDY_DID,
    )
    schema_name = fields.Str(
        description="Schema name",
        required=False,
        example="preferences",
    )
    schema_version = fields.Str(
        description="Schema version",
        required=False,
        **INDY_VERSION,
    )
    issuer_did = fields.Str(
        description="Credential issuer DID",
        required=False,
        **INDY_DID,
    )
    comment = fields.Str(description="Human-readable comment", required=False)
    credential_proposal = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialOfferRequestSchema(Schema):
    """Request schema for sending credential offer admin message."""

    connection_id = fields.UUID(
        description="Connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )
    auto_issue = fields.Bool(
        description=(
            "Whether to respond automatically to credential requests, creating "
            "and issuing requested credentials"
        ),
        required=False,
        default=False,
    )
    comment = fields.Str(description="Human-readable comment", required=False)
    credential_preview = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialIssueRequestSchema(Schema):
    """Request schema for sending credential issue admin message."""

    comment = fields.Str(description="Human-readable comment", required=False)
    credential_preview = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialProblemReportRequestSchema(Schema):
    """Request schema for sending problem report."""

    explain_ltxt = fields.Str(required=True)


@docs(tags=["issue-credential"], summary="Get attribute MIME types from wallet")
@response_schema(V10AttributeMimeTypesResultSchema(), 200)
async def attribute_mime_types_get(request: web.BaseRequest):
    """
    Request handler for getting credential attribute MIME types.

    Args:
        request: aiohttp request object

    Returns:
        The MIME types response

    """
    context = request.app["request_context"]
    credential_id = request.match_info["credential_id"]
    holder: BaseHolder = await context.inject(BaseHolder)

    return web.json_response(await holder.get_mime_type(credential_id))


@docs(tags=["issue-credential"], summary="Fetch all credential exchange records")
@response_schema(V10CredentialExchangeListResultSchema(), 200)
async def credential_exchange_list(request: web.BaseRequest):
    """
    Request handler for searching connection records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    if "thread_id" in request.query and request.query["thread_id"] != "":
        tag_filter["thread_id"] = request.query["thread_id"]
    post_filter = {}
    for param_name in ("connection_id", "role", "state"):
        if param_name in request.query and request.query[param_name] != "":
            post_filter[param_name] = request.query[param_name]
    records = await V10CredentialExchange.query(context, tag_filter, post_filter)
    return web.json_response({"results": [record.serialize() for record in records]})


@docs(tags=["issue-credential"], summary="Fetch a single credential exchange record")
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching single connection record.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    credential_exchange_id = request.match_info["cred_ex_id"]
    try:
        record = await V10CredentialExchange.retrieve_by_id(
            context, credential_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    return web.json_response(record.serialize())


@docs(tags=["issue-credential"], summary="Send credential, automating entire flow")
@request_schema(V10CredentialProposalRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_send(request: web.BaseRequest):
    """
    Request handler for sending credential from issuer to holder from attr values.

    If both issuer and holder are configured for automatic responses, the operation
    ultimately results in credential issue; otherwise, the result waits on the first
    response not automated; the credential exchange record retains state regardless.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    connection_id = body.get("connection_id")
    preview_spec = body.get("credential_proposal")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="credential_proposal must be provided.")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_proposal = CredentialProposal(
        comment=comment,
        credential_proposal=CredentialPreview.deserialize(preview_spec),
        **{t: body.get(t) for t in CRED_DEF_TAGS if body.get(t)},
    )

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await credential_manager.prepare_send(
        connection_id, credential_proposal=credential_proposal
    )
    await outbound_handler(
        credential_offer_message, connection_id=credential_exchange_record.connection_id
    )

    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["issue-credential"], summary="Send issuer a credential proposal")
@request_schema(V10CredentialProposalRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_send_proposal(request: web.BaseRequest):
    """
    Request handler for sending credential proposal.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    comment = body.get("comment")
    preview_spec = body.get("credential_proposal")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="credential_proposal must be provided.")

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_preview = CredentialPreview.deserialize(preview_spec)

    credential_manager = CredentialManager(context)

    credential_exchange_record = await credential_manager.create_proposal(
        connection_id,
        comment=comment,
        credential_preview=credential_preview,
        **{t: body.get(t) for t in CRED_DEF_TAGS if body.get(t)},
    )

    await outbound_handler(
        CredentialProposal.deserialize(
            credential_exchange_record.credential_proposal_dict
        ),
        connection_id=connection_id,
    )

    return web.json_response(credential_exchange_record.serialize())


@docs(
    tags=["issue-credential"],
    summary="Send holder a credential offer, free from reference to any proposal",
)
@request_schema(V10CredentialOfferRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_send_free_offer(request: web.BaseRequest):
    """
    Request handler for sending free credential offer.

    An issuer initiates a such a credential offer, which is free any
    holder-initiated corresponding proposal.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    cred_def_id = body.get("cred_def_id")
    auto_issue = body.get(
        "auto_issue", context.settings.get("debug.auto_respond_credential_request")
    )
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")

    if not cred_def_id:
        raise web.HTTPBadRequest(reason="cred_def_id is required")

    if auto_issue and not preview_spec:
        raise web.HTTPBadRequest(
            reason="If auto_issue is set to"
            + " true then credential_preview must also be provided."
        )

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    if preview_spec:
        credential_preview = CredentialPreview.deserialize(preview_spec)
        credential_proposal = CredentialProposal(
            comment=comment,
            credential_proposal=credential_preview,
            cred_def_id=cred_def_id,
        )
        credential_proposal_dict = credential_proposal.serialize()
    else:
        credential_proposal_dict = None

    credential_exchange_record = V10CredentialExchange(
        connection_id=connection_id,
        initiator=V10CredentialExchange.INITIATOR_SELF,
        credential_definition_id=cred_def_id,
        credential_proposal_dict=credential_proposal_dict,
        auto_issue=auto_issue,
    )

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await credential_manager.create_offer(
        credential_exchange_record, comment=comment
    )

    await outbound_handler(credential_offer_message, connection_id=connection_id)

    return web.json_response(credential_exchange_record.serialize())


@docs(
    tags=["issue-credential"],
    summary="Send holder a credential offer in reference to a proposal",
)
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_send_bound_offer(request: web.BaseRequest):
    """
    Request handler for sending bound credential offer.

    A holder initiates this sequence with a credential proposal; this message
    responds with an offer bound to the proposal.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    credential_exchange_record = await V10CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    assert credential_exchange_record.state == (
        V10CredentialExchange.STATE_PROPOSAL_RECEIVED
    )

    connection_id = credential_exchange_record.connection_id
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_offer_message,
    ) = await credential_manager.create_offer(credential_exchange_record, comment=None)

    await outbound_handler(credential_offer_message, connection_id=connection_id)

    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["issue-credential"], summary="Send a credential request")
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_send_request(request: web.BaseRequest):
    """
    Request handler for sending credential request.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    credential_exchange_record = await V10CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    connection_id = credential_exchange_record.connection_id

    assert credential_exchange_record.state == (
        V10CredentialExchange.STATE_OFFER_RECEIVED
    )

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_request_message,
    ) = await credential_manager.create_request(
        credential_exchange_record, connection_record.my_did
    )

    await outbound_handler(credential_request_message, connection_id=connection_id)
    return web.json_response(credential_exchange_record.serialize())


@docs(tags=["issue-credential"], summary="Send a credential")
@request_schema(V10CredentialIssueRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_issue(request: web.BaseRequest):
    """
    Request handler for sending credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")

    if not preview_spec:
        raise web.HTTPBadRequest(reason="credential_preview must be provided.")

    credential_exchange_id = request.match_info["cred_ex_id"]
    cred_exch_record = await V10CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    connection_id = cred_exch_record.connection_id

    assert cred_exch_record.state == V10CredentialExchange.STATE_REQUEST_RECEIVED

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_preview = CredentialPreview.deserialize(preview_spec)

    credential_manager = CredentialManager(context)

    (
        cred_exch_record,
        credential_issue_message,
    ) = await credential_manager.issue_credential(
        cred_exch_record,
        comment=comment,
        credential_values=credential_preview.attr_dict(decode=False),
    )

    await outbound_handler(credential_issue_message, connection_id=connection_id)
    return web.json_response(cred_exch_record.serialize())


@docs(tags=["issue-credential"], summary="Store a received credential")
@response_schema(V10CredentialExchangeSchema(), 200)
async def credential_exchange_store(request: web.BaseRequest):
    """
    Request handler for storing credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    credential_exchange_record = await V10CredentialExchange.retrieve_by_id(
        context, credential_exchange_id
    )
    connection_id = credential_exchange_record.connection_id

    assert credential_exchange_record.state == (
        V10CredentialExchange.STATE_CREDENTIAL_RECEIVED
    )

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        raise web.HTTPForbidden()

    credential_manager = CredentialManager(context)

    (
        credential_exchange_record,
        credential_stored_message,
    ) = await credential_manager.store_credential(credential_exchange_record)

    await outbound_handler(credential_stored_message, connection_id=connection_id)
    return web.json_response(credential_exchange_record.serialize())


@docs(
    tags=["issue-credential"], summary="Send a problem report for credential exchange"
)
@request_schema(V10CredentialProblemReportRequestSchema())
async def credential_exchange_problem_report(request: web.BaseRequest):
    """
    Request handler for sending problem report.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    body = await request.json()

    try:
        credential_exchange_record = await V10CredentialExchange.retrieve_by_id(
            context, credential_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    error_result = ProblemReport(explain_ltxt=body["explain_ltxt"])
    error_result.assign_thread_id(credential_exchange_record.thread_id)

    await outbound_handler(
        error_result, connection_id=credential_exchange_record.connection_id
    )
    return web.json_response({})


@docs(
    tags=["issue-credential"], summary="Remove an existing credential exchange record"
)
async def credential_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a credential exchange record.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    credential_exchange_id = request.match_info["cred_ex_id"]
    try:
        credential_exchange_record = await V10CredentialExchange.retrieve_by_id(
            context, credential_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    await credential_exchange_record.delete_record(context)
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/issue-credential/mime-types/{credential_id}", attribute_mime_types_get
            ),
            web.get("/issue-credential/records", credential_exchange_list),
            web.get(
                "/issue-credential/records/{cred_ex_id}", credential_exchange_retrieve
            ),
            web.post("/issue-credential/send", credential_exchange_send),
            web.post(
                "/issue-credential/send-proposal", credential_exchange_send_proposal
            ),
            web.post(
                "/issue-credential/send-offer", credential_exchange_send_free_offer
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/send-offer",
                credential_exchange_send_bound_offer,
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/send-request",
                credential_exchange_send_request,
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/issue",
                credential_exchange_issue,
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/store",
                credential_exchange_store,
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/problem-report",
                credential_exchange_problem_report,
            ),
            web.post(
                "/issue-credential/records/{cred_ex_id}/remove",
                credential_exchange_remove,
            ),
        ]
    )
