"""Out-of-band handling admin routes."""

import json
import logging

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate
from marshmallow.exceptions import ValidationError

from ....admin.decorators.auth import tenant_authentication
from ....admin.request_context import AdminRequestContext
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.models.paginated_query import (
    PaginatedQuerySchema,
    get_paginated_query_params,
)
from ....messaging.valid import UUID4_EXAMPLE, UUID4_VALIDATE
from ....storage.error import StorageError, StorageNotFoundError
from ...didcomm_prefix import DIDCommPrefix
from ...didexchange.v1_0.manager import DIDXManager, DIDXManagerError
from .manager import OutOfBandManager, OutOfBandManagerError
from .message_types import SPEC_URI
from .messages.invitation import HSProto, InvitationMessage, InvitationMessageSchema
from .models.invitation import InvitationRecordSchema
from .models.oob_record import OobRecord, OobRecordSchema

LOGGER = logging.getLogger(__name__)


class OutOfBandModuleResponseSchema(OpenAPISchema):
    """Response schema for Out of Band Module."""


class OobIdQueryStringSchema(OpenAPISchema):
    """Parameters and validators for fetch invitation request query string."""

    oob_id = fields.Str(
        required=True,
        validate=UUID4_VALIDATE,
        metadata={"description": "The Out of Band id to fetch"},
    )


class InvitationCreateQueryStringSchema(OpenAPISchema):
    """Parameters and validators for create invitation request query string."""

    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    multi_use = fields.Boolean(
        required=False,
        metadata={"description": "Create invitation for multiple use (default false)"},
    )
    create_unique_did = fields.Boolean(
        required=False,
        metadata={"description": "Create unique DID for this invitation (default false)"},
    )


class InvitationCreateRequestSchema(OpenAPISchema):
    """Invitation create request Schema."""

    class AttachmentDefSchema(OpenAPISchema):
        """Attachment Schema."""

        _id = fields.Str(
            data_key="id",
            metadata={
                "description": "Attachment identifier",
                "example": "attachment-0",
            },
        )
        _type = fields.Str(
            data_key="type",
            validate=validate.OneOf(["credential-offer", "present-proof"]),
            metadata={"description": "Attachment type", "example": "present-proof"},
        )

    attachments = fields.Nested(
        AttachmentDefSchema,
        many=True,
        required=False,
        metadata={"description": "Optional invitation attachments"},
    )
    handshake_protocols = fields.List(
        fields.Str(
            validate=lambda hsp: HSProto.get(hsp) is not None,
            metadata={
                "description": "Handshake protocol to specify in invitation",
                "example": DIDCommPrefix.qualify_current(HSProto.RFC23.name),
            },
        ),
        required=False,
    )
    accept = fields.List(
        fields.Str(),
        required=False,
        metadata={
            "description": (
                "List of mime type in order of preference that should be use in"
                " responding to the message"
            ),
            "example": ["didcomm/aip1", "didcomm/aip2;env=rfc19"],
        },
    )
    use_public_did = fields.Boolean(
        dump_default=False,
        metadata={
            "description": "Whether to use public DID in invitation",
            "example": False,
        },
    )
    use_did = fields.Str(
        required=False,
        metadata={
            "description": "DID to use in invitation",
            "example": "did:example:123",
        },
    )
    use_did_method = fields.Str(
        required=False,
        validate=validate.OneOf(DIDXManager.SUPPORTED_USE_DID_METHODS),
        metadata={
            "description": "DID method to use in invitation",
            "example": "did:peer:2",
        },
    )
    metadata = fields.Dict(
        required=False,
        metadata={
            "description": (
                "Optional metadata to attach to the connection created with the"
                " invitation"
            )
        },
    )
    my_label = fields.Str(
        required=False,
        metadata={
            "description": "Label for connection invitation",
            "example": "Invitation to Barry",
        },
    )
    protocol_version = fields.Str(
        required=False,
        metadata={"description": "OOB protocol version", "example": "1.1"},
    )
    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )
    goal_code = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested code the receiver may want to display to the user or"
                " use in automatically deciding what to do with the out-of-band message"
            ),
            "example": "issue-vc",
        },
    )
    goal = fields.Str(
        required=False,
        metadata={
            "description": (
                "A self-attested string that the receiver may want to display to the"
                " user about the context-specific goal of the out-of-band message"
            ),
            "example": "To issue a Faber College Graduate credential",
        },
    )


class InvitationReceiveQueryStringSchema(OpenAPISchema):
    """Parameters and validators for receive invitation request query string."""

    alias = fields.Str(
        required=False,
        metadata={"description": "Alias for connection", "example": "Barry"},
    )
    auto_accept = fields.Boolean(
        required=False,
        metadata={"description": "Auto-accept connection (defaults to configuration)"},
    )
    use_existing_connection = fields.Boolean(
        required=False,
        dump_default=True,
        metadata={"description": "Use an existing connection, if possible"},
    )
    mediation_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Identifier for active mediation record to be used",
            "example": UUID4_EXAMPLE,
        },
    )


class InvitationRecordResponseSchema(OpenAPISchema):
    """Response schema for Invitation Record."""


class InvitationRecordMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking invitation record."""

    invi_msg_id = fields.Str(
        required=True,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Invitation Message identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class OobInvitationRecordMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking invitation record."""

    oob_id = fields.Str(
        required=True,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "OOB Invitation identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class OobRecordListQueryStringSchema(PaginatedQuerySchema):
    """Parameters and validators for OOB record list request query string."""

    state = fields.Str(
        required=False,
        validate=validate.OneOf(
            OobRecord.get_attributes_by_prefix("STATE_", walk_mro=True)
        ),
        metadata={
            "description": "OOB record state",
            "example": OobRecord.STATE_INITIAL,
        },
    )
    role = fields.Str(
        required=False,
        validate=validate.OneOf(
            OobRecord.get_attributes_by_prefix("ROLE_", walk_mro=False)
        ),
        metadata={
            "description": "OOB record role",
            "example": OobRecord.ROLE_SENDER,
        },
    )
    connection_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Connection identifier",
            "example": UUID4_EXAMPLE,
        },
    )
    invi_msg_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Invitation message identifier",
            "example": UUID4_EXAMPLE,
        },
    )


class OobRecordListSchema(OpenAPISchema):
    """Result schema for OOB record list."""

    results = fields.List(
        fields.Nested(OobRecordSchema()),
        required=True,
        metadata={"description": "List of OOB records"},
    )


@docs(
    tags=["out-of-band"],
    summary="Query OOB records",
)
@querystring_schema(OobRecordListQueryStringSchema())
@response_schema(OobRecordListSchema(), 200, description="")
@tenant_authentication
async def oob_records_list(request: web.BaseRequest):
    """Request handler for searching OOB records.

    Args:
        request: aiohttp request object

    Returns:
        The OOB record list response

    """
    context: AdminRequestContext = request["context"]

    tag_filter = {
        k: request.query[k]
        for k in ("connection_id", "invi_msg_id")
        if request.query.get(k, "") != ""
    }
    post_filter = {
        k: request.query[k]
        for k in ("state", "role")
        if request.query.get(k, "") != ""
    }

    limit, offset, order_by, descending = get_paginated_query_params(request)

    profile = context.profile
    try:
        async with profile.session() as session:
            records = await OobRecord.query(
                session,
                tag_filter,
                limit=limit,
                offset=offset,
                order_by=order_by,
                descending=descending,
                post_filter_positive=post_filter,
            )
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["out-of-band"], summary="Fetch an existing Out-of-Band invitation.")
@querystring_schema(OobIdQueryStringSchema())
@response_schema(InvitationRecordResponseSchema(), description="")
@tenant_authentication
async def invitation_fetch(request: web.BaseRequest):
    """Request handler for fetching an invitation.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    oob_mgr = OutOfBandManager(profile)
    try:
        record = await oob_mgr.fetch_oob_invitation_record_by_id(
            request.query.get("oob_id")
        )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(record.serialize())


@docs(
    tags=["out-of-band"],
    summary="Create a new connection invitation",
)
@querystring_schema(InvitationCreateQueryStringSchema())
@request_schema(InvitationCreateRequestSchema())
@response_schema(InvitationRecordSchema(), description="")
@tenant_authentication
async def invitation_create(request: web.BaseRequest):
    """Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """
    context: AdminRequestContext = request["context"]

    body = await request.json() if request.body_exists else {}
    attachments = body.get("attachments")
    handshake_protocols = body.get("handshake_protocols", [])
    service_accept = body.get("accept")
    use_public_did = body.get("use_public_did", False)
    use_did = body.get("use_did")
    use_did_method = body.get("use_did_method")
    metadata = body.get("metadata")
    my_label = body.get("my_label")
    alias = body.get("alias")
    mediation_id = body.get("mediation_id")
    protocol_version = body.get("protocol_version")
    goal_code = body.get("goal_code")
    goal = body.get("goal")

    multi_use = json.loads(request.query.get("multi_use", "false"))
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    create_unique_did = json.loads(request.query.get("create_unique_did", "false"))

    profile = context.profile

    oob_mgr = OutOfBandManager(profile)
    try:
        invi_rec = await oob_mgr.create_invitation(
            my_label=my_label,
            auto_accept=auto_accept,
            public=use_public_did,
            use_did=use_did,
            use_did_method=use_did_method,
            hs_protos=[h for h in [HSProto.get(hsp) for hsp in handshake_protocols] if h],
            multi_use=multi_use,
            create_unique_did=create_unique_did,
            attachments=attachments,
            metadata=metadata,
            alias=alias,
            mediation_id=mediation_id,
            service_accept=service_accept,
            protocol_version=protocol_version,
            goal_code=goal_code,
            goal=goal,
        )
    except (StorageNotFoundError, ValidationError, OutOfBandManagerError) as e:
        raise web.HTTPBadRequest(reason=e.roll_up)

    return web.json_response(invi_rec.serialize())


@docs(
    tags=["out-of-band"],
    summary="Receive a new connection invitation",
)
@querystring_schema(InvitationReceiveQueryStringSchema())
@request_schema(InvitationMessageSchema())
@response_schema(OobRecordSchema(), 200, description="")
@tenant_authentication
async def invitation_receive(request: web.BaseRequest):
    """Request handler for receiving a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The out of band invitation details

    """

    context: AdminRequestContext = request["context"]
    if context.settings.get("admin.no_receive_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not allow receipt of invitations"
        )

    profile = context.profile
    oob_mgr = OutOfBandManager(profile)

    body = await request.json()
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    # By default, try to use an existing connection
    use_existing_conn = json.loads(request.query.get("use_existing_connection", "true"))
    mediation_id = request.query.get("mediation_id")
    try:
        invitation = InvitationMessage.deserialize(body)
        result = await oob_mgr.receive_invitation(
            invitation,
            auto_accept=auto_accept,
            alias=alias,
            use_existing_connection=use_existing_conn,
            mediation_id=mediation_id,
        )
    except (DIDXManagerError, StorageError, BaseModelError) as err:
        LOGGER.exception("Error during receive invitation")
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response(result.serialize())


@docs(tags=["out-of-band"], summary="Delete records associated with invitation")
@match_info_schema(InvitationRecordMatchInfoSchema())
@response_schema(InvitationRecordResponseSchema(), description="")
@tenant_authentication
async def invitation_remove(request: web.BaseRequest):
    """Request handler for removing a invitation related conn and oob records.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    invi_msg_id = request.match_info["invi_msg_id"]
    profile = context.profile
    oob_mgr = OutOfBandManager(profile)
    try:
        await oob_mgr.delete_conn_and_oob_record_invitation(invi_msg_id)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/out-of-band/create-invitation", invitation_create),
            web.post("/out-of-band/receive-invitation", invitation_receive),
            web.get(
                "/out-of-band/records",
                oob_records_list,
                allow_head=False,
            ),
            web.get(
                "/out-of-band/invitations",
                invitation_fetch,
                allow_head=False,
            ),
            web.delete("/out-of-band/invitations/{invi_msg_id}", invitation_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "out-of-band",
            "description": "Out-of-band connections",
            "externalDocs": {
                "description": "Design",
                "url": SPEC_URI,
            },
        }
    )
