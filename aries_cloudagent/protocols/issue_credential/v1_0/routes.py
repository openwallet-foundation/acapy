"""Credential exchange admin routes."""

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from json.decoder import JSONDecodeError
from marshmallow import fields, validate

from ...out_of_band.v1_0.models.oob_record import OobRecord
from ....wallet.util import default_did_from_verkey
from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....indy.holder import IndyHolderError
from ....indy.issuer import IndyIssuerError
from ....ledger.error import LedgerError
from ....messaging.credential_definitions.util import CRED_DEF_TAGS
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    UUIDFour,
    UUID4,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.tracing import trace_event, get_timer, AdminAPIMessageTracingSchema

from . import problem_report_for_record, report_problem
from .manager import CredentialManager, CredentialManagerError
from .message_types import SPEC_URI
from .messages.credential_problem_report import ProblemReportReason
from .messages.credential_proposal import CredentialProposal, CredentialProposalSchema
from .messages.inner.credential_preview import (
    CredentialPreview,
    CredentialPreviewSchema,
)
from .models.credential_exchange import (
    V10CredentialExchange,
    V10CredentialExchangeSchema,
)


class IssueCredentialModuleResponseSchema(OpenAPISchema):
    """Response schema for Issue Credential Module."""


class V10CredentialExchangeListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential exchange list query."""

    connection_id = fields.UUID(
        description="Connection identifier",
        required=False,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    thread_id = fields.UUID(
        description="Thread identifier",
        required=False,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    role = fields.Str(
        description="Role assigned in credential exchange",
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10CredentialExchange, m)
                for m in vars(V10CredentialExchange)
                if m.startswith("ROLE_")
            ]
        ),
    )
    state = fields.Str(
        description="Credential exchange state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10CredentialExchange, m)
                for m in vars(V10CredentialExchange)
                if m.startswith("STATE_")
            ]
        ),
    )


class V10CredentialExchangeListResultSchema(OpenAPISchema):
    """Result schema for Aries#0036 v1.0 credential exchange query."""

    results = fields.List(
        fields.Nested(V10CredentialExchangeSchema),
        description="Aries#0036 v1.0 credential exchange records",
    )


class V10CredentialStoreRequestSchema(OpenAPISchema):
    """Request schema for sending a credential store admin message."""

    credential_id = fields.Str(required=False)


class V10CredentialCreateSchema(AdminAPIMessageTracingSchema):
    """Base class for request schema for sending credential proposal admin message."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )
    schema_id = fields.Str(
        description="Schema identifier", required=False, **INDY_SCHEMA_ID
    )
    schema_issuer_did = fields.Str(
        description="Schema issuer DID", required=False, **INDY_DID
    )
    schema_name = fields.Str(
        description="Schema name", required=False, example="preferences"
    )
    schema_version = fields.Str(
        description="Schema version", required=False, **INDY_VERSION
    )
    issuer_did = fields.Str(
        description="Credential issuer DID", required=False, **INDY_DID
    )
    auto_remove = fields.Bool(
        description=(
            "Whether to remove the credential exchange record on completion "
            "(overrides --preserve-exchange-records configuration setting)"
        ),
        required=False,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    credential_proposal = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialProposalRequestSchemaBase(AdminAPIMessageTracingSchema):
    """Base class for request schema for sending credential proposal admin message."""

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
        description="Schema identifier", required=False, **INDY_SCHEMA_ID
    )
    schema_issuer_did = fields.Str(
        description="Schema issuer DID", required=False, **INDY_DID
    )
    schema_name = fields.Str(
        description="Schema name", required=False, example="preferences"
    )
    schema_version = fields.Str(
        description="Schema version", required=False, **INDY_VERSION
    )
    issuer_did = fields.Str(
        description="Credential issuer DID", required=False, **INDY_DID
    )
    auto_remove = fields.Bool(
        description=(
            "Whether to remove the credential exchange record on completion "
            "(overrides --preserve-exchange-records configuration setting)"
        ),
        required=False,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )


class V10CredentialProposalRequestOptSchema(V10CredentialProposalRequestSchemaBase):
    """Request schema for sending credential proposal on optional proposal preview."""

    credential_proposal = fields.Nested(CredentialPreviewSchema, required=False)


class V10CredentialProposalRequestMandSchema(V10CredentialProposalRequestSchemaBase):
    """Request schema for sending credential proposal on mandatory proposal preview."""

    credential_proposal = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialBoundOfferRequestSchema(OpenAPISchema):
    """Request schema for sending bound credential offer admin message."""

    counter_proposal = fields.Nested(
        CredentialProposalSchema,
        required=False,
        description="Optional counter-proposal",
    )


class V10CredentialFreeOfferRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for sending free credential offer admin message."""

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
    )
    auto_remove = fields.Bool(
        description=(
            "Whether to remove the credential exchange record on completion "
            "(overrides --preserve-exchange-records configuration setting)"
        ),
        required=False,
        default=True,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    credential_preview = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialConnFreeOfferRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for creating connection free credential offer."""

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
    )
    auto_remove = fields.Bool(
        description=(
            "Whether to remove the credential exchange record on completion "
            "(overrides --preserve-exchange-records configuration setting)"
        ),
        required=False,
        default=True,
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    credential_preview = fields.Nested(CredentialPreviewSchema, required=True)


class V10CredentialIssueRequestSchema(OpenAPISchema):
    """Request schema for sending credential issue admin message."""

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )


class V10CredentialProblemReportRequestSchema(OpenAPISchema):
    """Request schema for sending problem report."""

    description = fields.Str(required=True)


class CredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


class CredExIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential exchange id."""

    cred_ex_id = fields.Str(
        description="Credential exchange identifier", required=True, **UUID4
    )


@docs(
    tags=["issue-credential v1.0"],
    summary="Fetch all credential exchange records",
)
@querystring_schema(V10CredentialExchangeListQueryStringSchema)
@response_schema(V10CredentialExchangeListResultSchema(), 200, description="")
async def credential_exchange_list(request: web.BaseRequest):
    """
    Request handler for searching credential exchange records.

    Args:
        request: aiohttp request object

    Returns:
        The connection list response

    """
    context: AdminRequestContext = request["context"]
    tag_filter = {}
    if "thread_id" in request.query and request.query["thread_id"] != "":
        tag_filter["thread_id"] = request.query["thread_id"]
    post_filter = {
        k: request.query[k]
        for k in ("connection_id", "role", "state")
        if request.query.get(k, "") != ""
    }

    try:
        async with context.profile.session() as session:
            records = await V10CredentialExchange.query(
                session=session,
                tag_filter=tag_filter,
                post_filter_positive=post_filter,
            )
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(
    tags=["issue-credential v1.0"],
    summary="Fetch a single credential exchange record",
)
@match_info_schema(CredExIdMatchInfoSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching single credential exchange record.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    try:
        async with context.profile.session() as session:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )
        result = cred_ex_record.serialize()
    except StorageNotFoundError as err:
        # no such cred ex record: not protocol error, user fat-fingered id
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        # present but broken or hopeless: protocol error
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record,
            outbound_handler,
        )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary=(
        "Create a credential record without "
        "sending (generally for use with Out-Of-Band)"
    ),
)
@request_schema(V10CredentialCreateSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_create(request: web.BaseRequest):
    """
    Request handler for creating a credential from attr values.

    The internal credential record will be created without the credential
    being sent to any connection. This can be used in conjunction with
    the `oob` protocols to bind messages to an out of band message.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]

    body = await request.json()

    comment = body.get("comment")
    preview_spec = body.get("credential_proposal")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="credential_proposal must be provided")
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")

    try:
        preview = CredentialPreview.deserialize(preview_spec)

        credential_proposal = CredentialProposal(
            comment=comment,
            credential_proposal=preview,
            **{t: body.get(t) for t in CRED_DEF_TAGS if body.get(t)},
        )
        credential_proposal.assign_trace_decorator(
            context.settings,
            trace_msg,
        )

        trace_event(
            context.settings,
            credential_proposal,
            outcome="credential_exchange_create.START",
        )

        credential_manager = CredentialManager(context.profile)

        (
            credential_exchange_record,
            credential_offer_message,
        ) = await credential_manager.prepare_send(
            None,
            credential_proposal=credential_proposal,
            auto_remove=auto_remove,
            comment=comment,
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    trace_event(
        context.settings,
        credential_offer_message,
        outcome="credential_exchange_create.END",
        perf_counter=r_time,
    )

    return web.json_response(credential_exchange_record.serialize())


@docs(
    tags=["issue-credential v1.0"],
    summary="Send holder a credential, automating entire flow",
)
@request_schema(V10CredentialProposalRequestMandSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
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
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    connection_id = body.get("connection_id")
    preview_spec = body.get("credential_proposal")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="credential_proposal must be provided")
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")

    connection_record = None
    cred_ex_record = None
    try:
        preview = CredentialPreview.deserialize(preview_spec)
        async with profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            if not connection_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

        credential_proposal = CredentialProposal(
            comment=comment,
            credential_proposal=preview,
            **{t: body.get(t) for t in CRED_DEF_TAGS if body.get(t)},
        )
        credential_proposal.assign_trace_decorator(
            context.settings,
            trace_msg,
        )

        trace_event(
            context.settings,
            credential_proposal,
            outcome="credential_exchange_send.START",
        )

        credential_manager = CredentialManager(profile)
        (
            cred_ex_record,
            credential_offer_message,
        ) = await credential_manager.prepare_send(
            connection_id,
            credential_proposal=credential_proposal,
            auto_remove=auto_remove,
            comment=comment,
        )
        result = cred_ex_record.serialize()

    except (BaseModelError, CredentialManagerError, LedgerError, StorageError) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record or connection_record,
            outbound_handler,
        )

    await outbound_handler(
        credential_offer_message, connection_id=cred_ex_record.connection_id
    )

    trace_event(
        context.settings,
        credential_offer_message,
        outcome="credential_exchange_send.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send issuer a credential proposal",
)
@request_schema(V10CredentialProposalRequestOptSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_send_proposal(request: web.BaseRequest):
    """
    Request handler for sending credential proposal.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    comment = body.get("comment")
    preview_spec = body.get("credential_proposal")
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")

    connection_record = None
    cred_ex_record = None
    try:
        preview = CredentialPreview.deserialize(preview_spec) if preview_spec else None
        async with profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            if not connection_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

        credential_manager = CredentialManager(profile)
        cred_ex_record = await credential_manager.create_proposal(
            connection_id,
            comment=comment,
            credential_preview=preview,
            auto_remove=auto_remove,
            trace=trace_msg,
            **{t: body.get(t) for t in CRED_DEF_TAGS if body.get(t)},
        )

        credential_proposal = cred_ex_record.credential_proposal_dict
        result = cred_ex_record.serialize()

    except (BaseModelError, StorageError) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record or connection_record,
            outbound_handler,
        )

    await outbound_handler(
        credential_proposal,
        connection_id=connection_id,
    )

    trace_event(
        context.settings,
        credential_proposal,
        outcome="credential_exchange_send_proposal.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


async def _create_free_offer(
    profile: Profile,
    cred_def_id: str,
    connection_id: str = None,
    auto_issue: bool = False,
    auto_remove: bool = False,
    preview_spec: dict = None,
    comment: str = None,
    trace_msg: bool = None,
):
    """Create a credential offer and related exchange record."""

    credential_preview = CredentialPreview.deserialize(preview_spec)
    credential_proposal = CredentialProposal(
        comment=comment,
        credential_proposal=credential_preview,
        cred_def_id=cred_def_id,
    )
    credential_proposal.assign_trace_decorator(
        profile.settings,
        trace_msg,
    )
    credential_proposal_dict = credential_proposal.serialize()

    cred_ex_record = V10CredentialExchange(
        connection_id=connection_id,
        initiator=V10CredentialExchange.INITIATOR_SELF,
        role=V10CredentialExchange.ROLE_ISSUER,
        credential_definition_id=cred_def_id,
        credential_proposal_dict=credential_proposal_dict,
        auto_issue=auto_issue,
        auto_remove=auto_remove,
        trace=trace_msg,
    )

    credential_manager = CredentialManager(profile)

    (cred_ex_record, credential_offer_message) = await credential_manager.create_offer(
        cred_ex_record,
        counter_proposal=None,
        comment=comment,
    )

    return (cred_ex_record, credential_offer_message)


@docs(
    tags=["issue-credential v1.0"],
    summary="Create a credential offer, independent of any proposal or connection",
)
@request_schema(V10CredentialConnFreeOfferRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_create_free_offer(request: web.BaseRequest):
    """
    Request handler for creating free credential offer.

    Unlike with `send-offer`, this credential exchange is not tied to a specific
    connection. It must be dispatched out-of-band by the controller.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    body = await request.json()

    cred_def_id = body.get("cred_def_id")
    if not cred_def_id:
        raise web.HTTPBadRequest(reason="cred_def_id is required")

    auto_issue = body.get(
        "auto_issue", context.settings.get("debug.auto_respond_credential_request")
    )
    auto_remove = body.get("auto_remove")
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")
    if not preview_spec:
        raise web.HTTPBadRequest(reason=("Missing credential_preview"))

    trace_msg = body.get("trace")
    cred_ex_record = None
    try:
        (cred_ex_record, credential_offer_message) = await _create_free_offer(
            profile=profile,
            cred_def_id=cred_def_id,
            auto_issue=auto_issue,
            auto_remove=auto_remove,
            preview_spec=preview_spec,
            comment=comment,
            trace_msg=trace_msg,
        )
        result = cred_ex_record.serialize()
    except (
        BaseModelError,
        CredentialManagerError,
        IndyIssuerError,
        LedgerError,
        StorageError,
    ) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        raise web.HTTPBadRequest(reason=err.roll_up)
    trace_event(
        context.settings,
        credential_offer_message,
        outcome="credential_exchange_create_free_offer.END",
        perf_counter=r_time,
    )
    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send holder a credential offer, independent of any proposal",
)
@request_schema(V10CredentialFreeOfferRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_send_free_offer(request: web.BaseRequest):
    """
    Request handler for sending free credential offer.

    An issuer initiates a such a credential offer, free from any
    holder-initiated corresponding credential proposal with preview.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    cred_def_id = body.get("cred_def_id")
    if not cred_def_id:
        raise web.HTTPBadRequest(reason="cred_def_id is required")

    auto_issue = body.get(
        "auto_issue", context.settings.get("debug.auto_respond_credential_request")
    )
    auto_remove = body.get("auto_remove")
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")
    if not preview_spec:
        raise web.HTTPBadRequest(reason=("Missing credential_preview"))
    trace_msg = body.get("trace")

    cred_ex_record = None
    connection_record = None
    try:
        async with profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            if not connection_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

        cred_ex_record, credential_offer_message = await _create_free_offer(
            profile=profile,
            cred_def_id=cred_def_id,
            connection_id=connection_id,
            auto_issue=auto_issue,
            auto_remove=auto_remove,
            preview_spec=preview_spec,
            comment=comment,
            trace_msg=trace_msg,
        )
        result = cred_ex_record.serialize()

    except (
        StorageNotFoundError,
        BaseModelError,
        CredentialManagerError,
        LedgerError,
    ) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record or connection_record,
            outbound_handler,
        )

    await outbound_handler(credential_offer_message, connection_id=connection_id)

    trace_event(
        context.settings,
        credential_offer_message,
        outcome="credential_exchange_send_free_offer.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send holder a credential offer in reference to a proposal with preview",
)
@match_info_schema(CredExIdMatchInfoSchema())
@request_schema(V10CredentialBoundOfferRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
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
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json() if request.body_exists else {}
    proposal_spec = body.get("counter_proposal")

    credential_exchange_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    connection_record = None
    try:
        async with profile.session() as session:
            try:
                cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                    session, credential_exchange_id
                )
            except StorageNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err

            if cred_ex_record.state != (
                V10CredentialExchange.STATE_PROPOSAL_RECEIVED
            ):  # check state here: manager call creates free offers too
                raise CredentialManagerError(
                    f"Credential exchange {cred_ex_record.credential_exchange_id} "
                    f"in {cred_ex_record.state} state "
                    f"(must be {V10CredentialExchange.STATE_PROPOSAL_RECEIVED})"
                )

            connection_id = cred_ex_record.connection_id
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            if not connection_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

        credential_manager = CredentialManager(profile)
        (
            cred_ex_record,
            credential_offer_message,
        ) = await credential_manager.create_offer(
            cred_ex_record,
            counter_proposal=(
                CredentialProposal.deserialize(proposal_spec) if proposal_spec else None
            ),
            comment=None,
        )

        result = cred_ex_record.serialize()

    except (
        BaseModelError,
        CredentialManagerError,
        IndyIssuerError,
        LedgerError,
        StorageError,
    ) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record,
            outbound_handler,
        )

    await outbound_handler(credential_offer_message, connection_id=connection_id)

    trace_event(
        context.settings,
        credential_offer_message,
        outcome="credential_exchange_send_bound_offer.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send issuer a credential request",
)
@match_info_schema(CredExIdMatchInfoSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_send_request(request: web.BaseRequest):
    """
    Request handler for sending credential request.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]

    cred_ex_record = None
    connection_record = None

    async with profile.session() as session:
        try:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        # Fetch connection if exchange has record
        connection_record = None
        if cred_ex_record.connection_id:
            try:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, cred_ex_record.connection_id
                )
            except StorageNotFoundError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection_record and not connection_record.is_ready:
        raise web.HTTPForbidden(
            reason=f"Connection {connection_record.connection_id} not ready"
        )

    if connection_record:
        holder_did = connection_record.my_did
    else:
        # Need to get the holder DID from the out of band record
        async with profile.session() as session:
            oob_record = await OobRecord.retrieve_by_tag_filter(
                session,
                {"invi_msg_id": cred_ex_record.credential_offer_dict._thread.pthid},
            )
            # Transform recipient key into did
            holder_did = default_did_from_verkey(oob_record.our_recipient_key)

    try:
        credential_manager = CredentialManager(profile)
        (
            cred_ex_record,
            credential_request_message,
        ) = await credential_manager.create_request(cred_ex_record, holder_did)

        result = cred_ex_record.serialize()

    except (
        BaseModelError,
        CredentialManagerError,
        IndyHolderError,
        LedgerError,
        StorageError,
    ) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record,
            outbound_handler,
        )

    await outbound_handler(
        credential_request_message, connection_id=cred_ex_record.connection_id
    )

    trace_event(
        context.settings,
        credential_request_message,
        outcome="credential_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send holder a credential",
)
@match_info_schema(CredExIdMatchInfoSchema())
@request_schema(V10CredentialIssueRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_issue(request: web.BaseRequest):
    """
    Request handler for sending credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()
    comment = body.get("comment")

    credential_exchange_id = request.match_info["cred_ex_id"]

    cred_ex_record = None
    connection_record = None

    async with profile.session() as session:
        try:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        # Fetch connection if exchange has record
        connection_record = None
        if cred_ex_record.connection_id:
            try:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, cred_ex_record.connection_id
                )
            except StorageNotFoundError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection_record and not connection_record.is_ready:
        raise web.HTTPForbidden(
            reason=f"Connection {connection_record.connection_id} not ready"
        )

    try:
        credential_manager = CredentialManager(profile)
        (
            cred_ex_record,
            credential_issue_message,
        ) = await credential_manager.issue_credential(cred_ex_record, comment=comment)

        result = cred_ex_record.serialize()

    except (
        BaseModelError,
        CredentialManagerError,
        IndyIssuerError,
        LedgerError,
        StorageError,
    ) as err:
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record,
            outbound_handler,
        )

    await outbound_handler(
        credential_issue_message, connection_id=cred_ex_record.connection_id
    )

    trace_event(
        context.settings,
        credential_issue_message,
        outcome="credential_exchange_issue.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Store a received credential",
)
@match_info_schema(CredExIdMatchInfoSchema())
@request_schema(V10CredentialStoreRequestSchema())
@response_schema(V10CredentialExchangeSchema(), 200, description="")
async def credential_exchange_store(request: web.BaseRequest):
    """
    Request handler for storing credential.

    Args:
        request: aiohttp request object

    Returns:
        The credential exchange record

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    try:
        body = await request.json() or {}
        credential_id = body.get("credential_id")
    except JSONDecodeError:
        credential_id = None

    credential_exchange_id = request.match_info["cred_ex_id"]

    cred_ex_record = None
    connection_record = None

    async with profile.session() as session:
        try:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        # Fetch connection if exchange has record
        if cred_ex_record.connection_id:
            try:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, cred_ex_record.connection_id
                )
            except StorageNotFoundError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection_record and not connection_record.is_ready:
        raise web.HTTPForbidden(
            reason=f"Connection {connection_record.connection_id} not ready"
        )

    try:
        credential_manager = CredentialManager(profile)
        cred_ex_record = await credential_manager.store_credential(
            cred_ex_record,
            credential_id,
        )

    except (
        CredentialManagerError,
        IndyHolderError,
        StorageError,
    ) as err:  # treat failure to store as mangled on receipt hence protocol error
        if cred_ex_record:
            async with profile.session() as session:
                await cred_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ISSUANCE_ABANDONED.value,
            web.HTTPBadRequest,
            cred_ex_record,
            outbound_handler,
        )

    try:  # protocol owes an ack
        (
            cred_ex_record,
            credential_ack_message,
        ) = await credential_manager.send_credential_ack(cred_ex_record)
        result = cred_ex_record.serialize()  # pick up state done

    except (
        BaseModelError,
        CredentialManagerError,
        StorageError,
    ) as err:
        # protocol finished OK: do not send problem report nor set record state error
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    trace_event(
        context.settings,
        credential_ack_message,
        outcome="credential_exchange_store.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v1.0"],
    summary="Send a problem report for credential exchange",
)
@match_info_schema(CredExIdMatchInfoSchema())
@request_schema(V10CredentialProblemReportRequestSchema())
@response_schema(IssueCredentialModuleResponseSchema(), 200, description="")
async def credential_exchange_problem_report(request: web.BaseRequest):
    """
    Request handler for sending problem report.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    body = await request.json()
    description = body["description"]

    try:
        async with context.profile.session() as session:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )

            if not cred_ex_record.connection_id:
                raise web.HTTPBadRequest(
                    reason="No connection associated with credential exchange."
                )
            report = problem_report_for_record(cred_ex_record, description)
            await cred_ex_record.save_error_state(
                session,
                reason=f"created problem report: {description}",
            )
    except StorageNotFoundError as err:  # other party does not care about meta-problems
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(report, connection_id=cred_ex_record.connection_id)

    return web.json_response({})


@docs(
    tags=["issue-credential v1.0"],
    summary="Remove an existing credential exchange record",
)
@match_info_schema(CredExIdMatchInfoSchema())
@response_schema(IssueCredentialModuleResponseSchema(), 200, description="")
async def credential_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a credential exchange record.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]

    credential_exchange_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    try:
        async with context.profile.session() as session:
            cred_ex_record = await V10CredentialExchange.retrieve_by_id(
                session, credential_exchange_id
            )
            await cred_ex_record.delete_record(session)
    except StorageNotFoundError as err:  # not a protocol error
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:  # not a protocol error
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/issue-credential/records", credential_exchange_list, allow_head=False
            ),
            web.post(
                "/issue-credential/create-offer", credential_exchange_create_free_offer
            ),
            web.get(
                "/issue-credential/records/{cred_ex_id}",
                credential_exchange_retrieve,
                allow_head=False,
            ),
            web.post("/issue-credential/create", credential_exchange_create),
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
            web.delete(
                "/issue-credential/records/{cred_ex_id}",
                credential_exchange_remove,
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
            "name": "issue-credential v1.0",
            "description": "Credential issue v1.0",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
