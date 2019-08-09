"""Admin routes for presentations."""

import json

from aiohttp import web
from aiohttp_apispec import docs, request_schema, response_schema
from marshmallow import fields, Schema

from ....holder.base import BaseHolder
from ....storage.error import StorageNotFoundError

from ...connections.models.connection_record import ConnectionRecord

from .manager import PresentationManager
from .messages.inner.presentation_preview import (
    PresentationPreview,
    PresentationPreviewSchema
)
from .messages.presentation_proposal import PresentationProposal
from .models.presentation_exchange import (
    V10PresentationExchange,
    V10PresentationExchangeSchema,
)


class V10PresentationExchangeListSchema(Schema):
    """Result schema for an Aries#0037 v1.0 presentation exchange query."""

    results = fields.List(
        fields.Nested(V10PresentationExchangeSchema()),
        description="Aries#0037 v1.0 presentation exchange records"
    )


class V10PresentationProposalRequestSchema(Schema):
    """Request schema for sending a presentation proposal admin message."""

    connection_id = fields.UUID(description="Connection identifier", required=True)
    comment = fields.Str(
        description="Human-readable comment",
        required=False,
        default="")
    presentation_proposal = fields.Nested(PresentationPreviewSchema, required=True)
    auto_present = fields.Boolean(
        description=(
            "Whether to respond automatically to presentation requests, building "
            "and presenting requested proof"
        ),
        required=False,
        default=False
    )


class V10PresentationProposalResultSchema(V10PresentationExchangeSchema):
    """Result schema for sending a presentation proposal admin message."""


class V10PresentationRequestRequestSchema(Schema):
    """Request schema for sending a proof request."""

    connection_id = fields.UUID(description="Connection identifier", required=True)
    name = fields.String(example="proof-request", description="Proof request name")
    version = fields.String(example="1.0", description="Proof request version")
    comment = fields.String(
        description="Human-readable comment",
        required=False,
        default=""
    )
    presentation_proposal = fields.Nested(PresentationPreviewSchema, required=True)


class V10PresentationRequestResultSchema(V10PresentationExchangeSchema):
    """Result schema for sending a presentation request admin message."""


class IndyRequestedCredsRequestedAttrSchema(Schema):
    """Schema for requested attributes within indy requested credentials structure."""

    cred_id = fields.Str(
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        description=(
            "Wallet credential identifier (typically but not necessarily a UUID)"
        )
    )
    revealed = fields.Bool(
        description="Whether to reveal attribute in proof",
        default=True
    )


class IndyRequestedCredsRequestedPredSchema(Schema):
    """Schema for requested predicates within indy requested credentials structure."""

    cred_id = fields.Str(
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        description=(
            "Wallet credential identifier (typically but not necessarily a UUID)"
        )
    )


class V10PresentationRequestSchema(Schema):
    """Request schema for sending a presentation."""

    self_attested_attributes = fields.Dict(
        description=("Self-attested attributes to build into proof"),
        required=True,
        keys=fields.Str(example="attr_name"),  # marshmallow/apispec v3.0rc3 ignores
        values=fields.Str(
            example="self_attested_value",
            description=(
                "Self-attested attribute values to use in requested-credentials "
                "structure for proof construction"
            )
        )
    )
    requested_attributes = fields.Dict(
        description=(
            "Nested object mapping proof request attribute referents to "
            "requested-attribute specifiers"
        ),
        required=True,
        keys=fields.Str(example="attr_referent"),  # marshmallow/apispec v3.0rc3 ignores
        values=fields.Nested(IndyRequestedCredsRequestedAttrSchema())
    )
    requested_predicates = fields.Dict(
        description=(
            "Nested object mapping proof request predicate referents to "
            "requested-predicate specifiers"
        ),
        required=True,
        keys=fields.Str(example="pred_referent"),  # marshmallow/apispec v3.0rc3 ignores
        values=fields.Nested(IndyRequestedCredsRequestedPredSchema())
    )


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Fetch all present-proof exchange records"
)
@response_schema(V10PresentationExchangeListSchema(), 200)
async def presentation_exchange_list(request: web.BaseRequest):
    """
    Request handler for searching presentation exchange records.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange list response

    """
    context = request.app["request_context"]
    tag_filter = {}
    for param_name in (
        "connection_id",
        "thread_id",
        "initiator",
        "state",
        "verified"
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]
    records = await V10PresentationExchange.query(context, tag_filter)
    return web.json_response({"results": [record.serialize() for record in records]})


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Fetch a single presentation exchange record"
)
@response_schema(V10PresentationExchangeSchema(), 200)
async def presentation_exchange_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single presentation exchange record.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange record response

    """
    context = request.app["request_context"]
    presentation_exchange_id = request.match_info["pres_ex_id"]
    try:
        record = await V10PresentationExchange.retrieve_by_id(
            context,
            presentation_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()
    return web.json_response(record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Fetch credentials for a presentation request from wallet",
    parameters=[
        {
            "name": "start",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "count",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
        {
            "name": "extra_query",
            "in": "query",
            "schema": {"type": "string"},
            "required": False,
        },
    ]
)
async def presentation_exchange_credentials_list(request: web.BaseRequest):
    """
    Request handler for searching applicable credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context = request.app["request_context"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    presentation_referent = request.match_info["referent"]

    try:
        presentation_exchange_record = await V10PresentationExchange.retrieve_by_id(
            context,
            presentation_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json extra_query
    encoded_extra_query = request.query.get("extra_query") or "{}"
    extra_query = json.loads(encoded_extra_query)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    holder: BaseHolder = await context.inject(BaseHolder)
    credentials = await holder.get_credentials_for_presentation_request_by_referent(
        presentation_exchange_record.presentation_request,
        (presentation_referent,) if presentation_referent else (),
        start,
        count,
        extra_query
    )

    return web.json_response(credentials)


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Sends a presentation request"
)
@request_schema(V10PresentationProposalRequestSchema())
@response_schema(V10PresentationProposalResultSchema(), 200)
async def presentation_exchange_send_proposal(request: web.BaseRequest):
    """
    Request handler for sending a presentation proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context,
            connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        return web.HTTPForbidden()

    comment = body.get("comment")
    # Aries#0037 calls it a proposal in the proposal struct but it's of type preview
    presentation_preview = body.get("presentation_proposal")
    presentation_proposal_message = PresentationProposal(
        comment=comment,
        presentation_proposal=PresentationPreview.deserialize(presentation_preview)
    )
    auto_present = body.get(
        "auto_present",
        context.settings.get("debug.auto_respond_presentation_request")
    )

    presentation_manager = PresentationManager(context)

    presentation_exchange_record = (
        await presentation_manager.create_exchange_for_proposal(
            connection_id=connection_id,
            presentation_proposal_message=presentation_proposal_message,
            auto_present=auto_present
        )
    )
    await outbound_handler(presentation_proposal_message, connection_id=connection_id)

    return web.json_response(presentation_exchange_record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Sends a free presentation request not bound to any proposal"
)
@request_schema(V10PresentationRequestRequestSchema())
@response_schema(V10PresentationRequestResultSchema(), 200)
async def presentation_exchange_send_free_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request free from any proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context,
            connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        return web.HTTPForbidden()

    comment = body.get("comment")
    name = body.get("name", "proof-request")
    version = body.get("version", "1.0")
    presentation_proposal = body.get("presentation_proposal")
    presentation_proposal_message = PresentationProposal(
        comment=comment,
        presentation_proposal=PresentationPreview.deserialize(presentation_proposal)
    )

    presentation_exchange_record = V10PresentationExchange(
        connection_id=connection_id,
        initiator=V10PresentationExchange.INITIATOR_SELF,
        presentation_proposal_dict=presentation_proposal_message.serialize()
    )

    presentation_manager = PresentationManager(context)

    (
        presentation_exchange_record,
        presentation_request_message,
    ) = await presentation_manager.create_request(
        presentation_exchange_record,
        name=name,
        version=version,
        comment=comment
    )

    await outbound_handler(presentation_request_message, connection_id=connection_id)

    return web.json_response(presentation_exchange_record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Sends a presentation request in reference to a proposal"
)
@request_schema(V10PresentationRequestRequestSchema())
@response_schema(V10PresentationRequestResultSchema(), 200)
async def presentation_exchange_send_bound_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request free from any proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    presentation_exchange_record = await V10PresentationExchange.retrieve_by_id(
        context,
        presentation_exchange_id
    )
    assert presentation_exchange_record.state == (
        V10PresentationExchange.STATE_PROPOSAL_RECEIVED
    )
    body = await request.json()

    connection_id = body.get("connection_id")
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context,
            connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        return web.HTTPForbidden()

    presentation_manager = PresentationManager(context)

    (
        presentation_exchange_record,
        presentation_request_message
    ) = await presentation_manager.create_request(
        presentation_exchange_record
    )

    await outbound_handler(presentation_request_message, connection_id=connection_id)

    return web.json_response(presentation_exchange_record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Sends a proof presentation"
)
@request_schema(V10PresentationRequestSchema())
@response_schema(V10PresentationExchangeSchema())
async def presentation_exchange_send_presentation(request: web.BaseRequest):
    """
    Request handler for sending a presentation.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    presentation_exchange_id = request.match_info["pres_ex_id"]
    presentation_exchange_record = await V10PresentationExchange.retrieve_by_id(
        context, presentation_exchange_id
    )

    body = await request.json()

    connection_id = presentation_exchange_record.connection_id
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context,
            connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        return web.HTTPForbidden()

    assert (
        presentation_exchange_record.state
    ) == V10PresentationExchange.STATE_REQUEST_RECEIVED

    presentation_manager = PresentationManager(context)

    (
        presentation_exchange_record,
        presentation_message,
    ) = await presentation_manager.create_presentation(
        presentation_exchange_record,
        {
            "self_attested_attributes": body.get("self_attested_attributes"),
            "requested_attributes": body.get("requested_attributes"),
            "requested_predicates": body.get("requested_predicates")
        },
        comment=body.get("comment")
    )

    await outbound_handler(presentation_message, connection_id=connection_id)
    return web.json_response(presentation_exchange_record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Verify a received presentation"
)
@response_schema(V10PresentationExchangeSchema())
async def presentation_exchange_verify_presentation(
    request: web.BaseRequest
):
    """
    Request handler for verifying a presentation request.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    context = request.app["request_context"]
    presentation_exchange_id = request.match_info["pres_ex_id"]

    presentation_exchange_record = await V10PresentationExchange.retrieve_by_id(
        context,
        presentation_exchange_id
    )
    connection_id = presentation_exchange_record.connection_id

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context,
            connection_id
        )
    except StorageNotFoundError:
        raise web.HTTPBadRequest()

    if not connection_record.is_ready:
        return web.HTTPForbidden()

    assert (
        presentation_exchange_record.state
    ) == V10PresentationExchange.STATE_PRESENTATION_RECEIVED

    presentation_manager = PresentationManager(context)

    presentation_exchange_record = await presentation_manager.verify_presentation(
        presentation_exchange_record
    )

    return web.json_response(presentation_exchange_record.serialize())


@docs(
    tags=["*EXPERIMENTAL* Aries#0037 v1.0 present-proof exchange"],
    summary="Remove an existing presentation exchange record",
)
async def presentation_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a presentation exchange record.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    presentation_exchange_id = request.match_info["pres_ex_id"]
    try:
        presentation_exchange_record = await V10PresentationExchange.retrieve_by_id(
            context,
            presentation_exchange_id
        )
    except StorageNotFoundError:
        raise web.HTTPNotFound()

    await presentation_exchange_record.delete_record(context)
    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/v1.0/present_proof_exchange", presentation_exchange_list),
            web.get(
                "/v1.0/present_proof_exchange/{pres_ex_id}",
                presentation_exchange_retrieve
            ),
            web.get(
                "/v1.0/present_proof_exchange/{pres_ex_id}/credentials/{referent}",
                presentation_exchange_credentials_list,
            ),
            web.post(
                "/v1.0/present_proof_exchange/send_proposal",
                presentation_exchange_send_proposal,
            ),
            web.post(
                "/v1.0/present_proof_exchange/send_request",
                presentation_exchange_send_free_request,
            ),
            web.post(
                "/v1.0/present_proof_exchange/{pres_ex_id}/send_request",
                presentation_exchange_send_bound_request,
            ),
            web.post(
                "/v1.0/present_proof_exchange/{pres_ex_id}/send_presentation",
                presentation_exchange_send_presentation,
            ),
            web.post(
                "/v1.0/present_proof_exchange/{pres_ex_id}/verify_presentation",
                presentation_exchange_verify_presentation,
            ),
            web.post(
                "/v1.0/present_proof_exchange/{pres_ex_id}/remove",
                presentation_exchange_remove
            ),
        ]
    )
