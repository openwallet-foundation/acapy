"""Admin routes for presentations."""

import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....indy.holder import IndyHolder, IndyHolderError
from ....indy.models.cred_precis import IndyCredPrecisSchema
from ....indy.models.pres_preview import IndyPresPreview, IndyPresPreviewSchema
from ....indy.models.proof import IndyPresSpecSchema
from ....indy.models.proof_request import IndyProofRequestSchema
from ....indy.util import generate_pr_nonce
from ....ledger.error import LedgerError
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    INDY_EXTRA_WQL_EXAMPLE,
    INDY_EXTRA_WQL_VALIDATE,
    NUM_STR_NATURAL_EXAMPLE,
    NUM_STR_NATURAL_VALIDATE,
    NUM_STR_WHOLE_EXAMPLE,
    NUM_STR_WHOLE_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.tracing import AdminAPIMessageTracingSchema, get_timer, trace_event
from ....wallet.error import WalletNotFoundError
from . import problem_report_for_record, report_problem
from .manager import PresentationManager, PresentationManagerError
from .message_types import ATTACH_DECO_IDS, PRESENTATION_REQUEST, SPEC_URI
from .messages.presentation_problem_report import ProblemReportReason
from .messages.presentation_proposal import PresentationProposal
from .messages.presentation_request import PresentationRequest
from .models.presentation_exchange import (
    V10PresentationExchange,
    V10PresentationExchangeSchema,
)


class V10PresentProofModuleResponseSchema(OpenAPISchema):
    """Response schema for Present Proof Module."""


class V10PresentationExchangeListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for presentation exchange list query."""

    connection_id = fields.UUID(
        required=False,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )
    thread_id = fields.UUID(
        required=False,
        metadata={"description": "Thread identifier", "example": UUID4_EXAMPLE},
    )
    role = fields.Str(
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10PresentationExchange, m)
                for m in vars(V10PresentationExchange)
                if m.startswith("ROLE_")
            ]
        ),
        metadata={"description": "Role assigned in presentation exchange"},
    )
    state = fields.Str(
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10PresentationExchange, m)
                for m in vars(V10PresentationExchange)
                if m.startswith("STATE_")
            ]
        ),
        metadata={"description": "Presentation exchange state"},
    )


class V10PresentationExchangeListSchema(OpenAPISchema):
    """Result schema for an Aries RFC 37 v1.0 presentation exchange query."""

    results = fields.List(
        fields.Nested(V10PresentationExchangeSchema()),
        metadata={"description": "Aries RFC 37 v1.0 presentation exchange records"},
    )


class V10PresentationSendRequestSchema(IndyPresSpecSchema):
    """Request schema for sending a presentation."""

    auto_remove = fields.Bool(
        required=False,
        dump_default=False,
        metadata={
            "description": (
                "Whether to remove the presentation exchange record on completion"
                " (overrides --preserve-exchange-records configuration setting)"
            )
        },
    )


class V10PresentationProposalRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for sending a presentation proposal admin message."""

    connection_id = fields.UUID(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )
    comment = fields.Str(
        required=False,
        allow_none=True,
        metadata={"description": "Human-readable comment"},
    )
    presentation_proposal = fields.Nested(IndyPresPreviewSchema(), required=True)
    auto_present = fields.Boolean(
        required=False,
        dump_default=False,
        metadata={
            "description": (
                "Whether to respond automatically to presentation requests, building"
                " and presenting requested proof"
            )
        },
    )
    auto_remove = fields.Bool(
        required=False,
        dump_default=False,
        metadata={
            "description": (
                "Whether to remove the presentation exchange record on completion"
                " (overrides --preserve-exchange-records configuration setting)"
            )
        },
    )
    trace = fields.Bool(
        required=False,
        metadata={
            "description": "Whether to trace event (default false)",
            "example": False,
        },
    )


class V10PresentationCreateRequestRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for creating a proof request free of any connection."""

    proof_request = fields.Nested(IndyProofRequestSchema(), required=True)
    comment = fields.Str(required=False, allow_none=True)
    auto_verify = fields.Bool(
        required=False,
        metadata={
            "description": "Verifier choice to auto-verify proof presentation",
            "example": False,
        },
    )
    auto_remove = fields.Bool(
        required=False,
        dump_default=False,
        metadata={
            "description": (
                "Whether to remove the presentation exchange record on completion"
                " (overrides --preserve-exchange-records configuration setting)"
            )
        },
    )
    trace = fields.Bool(
        required=False,
        metadata={
            "description": "Whether to trace event (default false)",
            "example": False,
        },
    )


class V10PresentationSendRequestRequestSchema(
    V10PresentationCreateRequestRequestSchema
):
    """Request schema for sending a proof request on a connection."""

    connection_id = fields.UUID(
        required=True,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class V10PresentationSendRequestToProposalSchema(AdminAPIMessageTracingSchema):
    """Request schema for sending a proof request bound to a proposal."""

    auto_verify = fields.Bool(
        required=False,
        metadata={
            "description": "Verifier choice to auto-verify proof presentation",
            "example": False,
        },
    )
    auto_remove = fields.Bool(
        required=False,
        dump_default=False,
        metadata={
            "description": (
                "Whether to remove the presentation exchange record on completion"
                " (overrides --preserve-exchange-records configuration setting)"
            )
        },
    )
    trace = fields.Bool(
        required=False,
        metadata={
            "description": "Whether to trace event (default false)",
            "example": False,
        },
    )


class CredentialsFetchQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credentials fetch request query string."""

    referent = fields.Str(
        required=False,
        metadata={
            "description": "Proof request referents of interest, comma-separated",
            "example": "1_name_uuid,2_score_uuid",
        },
    )
    start = fields.Str(
        required=False,
        validate=NUM_STR_WHOLE_VALIDATE,
        metadata={
            "description": "Start index",
            "strict": True,
            "example": NUM_STR_WHOLE_EXAMPLE,
        },
    )
    count = fields.Str(
        required=False,
        validate=NUM_STR_NATURAL_VALIDATE,
        metadata={
            "description": "Maximum number to retrieve",
            "example": NUM_STR_NATURAL_EXAMPLE,
        },
    )
    extra_query = fields.Str(
        required=False,
        validate=INDY_EXTRA_WQL_VALIDATE,
        metadata={
            "description": "(JSON) object mapping referents to extra WQL queries",
            "example": INDY_EXTRA_WQL_EXAMPLE,
        },
    )


class V10PresentationProblemReportRequestSchema(OpenAPISchema):
    """Request schema for sending problem report."""

    description = fields.Str(required=True)


class V10PresExIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking presentation exchange id."""

    pres_ex_id = fields.Str(
        required=True,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Presentation exchange identifier",
            "example": UUID4_EXAMPLE,
        },
    )


@docs(tags=["present-proof v1.0"], summary="Fetch all present-proof exchange records")
@querystring_schema(V10PresentationExchangeListQueryStringSchema)
@response_schema(V10PresentationExchangeListSchema(), 200, description="")
async def presentation_exchange_list(request: web.BaseRequest):
    """
    Request handler for searching presentation exchange records.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange list response

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
            records = await V10PresentationExchange.query(
                session=session,
                tag_filter=tag_filter,
                post_filter_positive=post_filter,
            )
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(
    tags=["present-proof v1.0"],
    summary="Fetch a single presentation exchange record",
)
@match_info_schema(V10PresExIdMatchInfoSchema())
@response_schema(V10PresentationExchangeSchema(), 200, description="")
async def presentation_exchange_retrieve(request: web.BaseRequest):
    """
    Request handler for fetching a single presentation exchange record.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange record response

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = None
    try:
        async with profile.session() as session:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
        result = pres_ex_record.serialize()
    except StorageNotFoundError as err:
        # no such pres ex record: not protocol error, user fat-fingered id
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        # present but broken or hopeless: protocol error
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ABANDONED.value,
            web.HTTPBadRequest,
            pres_ex_record,
            outbound_handler,
        )

    return web.json_response(result)


@docs(
    tags=["present-proof v1.0"],
    summary="Fetch credentials for a presentation request from wallet",
)
@match_info_schema(V10PresExIdMatchInfoSchema())
@querystring_schema(CredentialsFetchQueryStringSchema())
@response_schema(IndyCredPrecisSchema(many=True), 200, description="")
async def presentation_exchange_credentials_list(request: web.BaseRequest):
    """
    Request handler for searching applicable credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    referents = request.query.get("referent")
    presentation_referents = (
        (r.strip() for r in referents.split(",")) if referents else ()
    )

    try:
        async with profile.session() as session:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    start = request.query.get("start")
    count = request.query.get("count")

    # url encoded json extra_query
    encoded_extra_query = request.query.get("extra_query") or "{}"
    extra_query = json.loads(encoded_extra_query)

    # defaults
    start = int(start) if isinstance(start, str) else 0
    count = int(count) if isinstance(count, str) else 10

    holder = profile.inject(IndyHolder)
    try:
        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            pres_ex_record._presentation_request.ser,
            presentation_referents,
            start,
            count,
            extra_query,
        )
    except IndyHolderError as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        await report_problem(
            err,
            ProblemReportReason.ABANDONED.value,
            web.HTTPBadRequest,
            pres_ex_record,
            outbound_handler,
        )

    pres_ex_record.log_state(
        "Retrieved presentation credentials",
        {
            "presentation_exchange_id": presentation_exchange_id,
            "referents": presentation_referents,
            "extra_query": extra_query,
            "credentials": credentials,
        },
        settings=context.settings,
    )
    return web.json_response(credentials)


@docs(tags=["present-proof v1.0"], summary="Sends a presentation proposal")
@request_schema(V10PresentationProposalRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200, description="")
async def presentation_exchange_send_proposal(request: web.BaseRequest):
    """
    Request handler for sending a presentation proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    connection_id = body.get("connection_id")

    # Aries RFC 37 calls it a proposal in the proposal struct but it's of type preview
    presentation_preview = body.get("presentation_proposal")
    connection_record = None
    async with profile.session() as session:
        try:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            presentation_proposal_message = PresentationProposal(
                comment=comment,
                presentation_proposal=IndyPresPreview.deserialize(presentation_preview),
            )
        except (BaseModelError, StorageError) as err:
            # other party does not care about our false protocol start
            raise web.HTTPBadRequest(reason=err.roll_up)

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

    trace_msg = body.get("trace")
    presentation_proposal_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    auto_present = body.get(
        "auto_present", context.settings.get("debug.auto_respond_presentation_request")
    )
    auto_remove = body.get("auto_remove")

    presentation_manager = PresentationManager(profile)
    pres_ex_record = None
    try:
        pres_ex_record = await presentation_manager.create_exchange_for_proposal(
            connection_id=connection_id,
            presentation_proposal_message=presentation_proposal_message,
            auto_present=auto_present,
            auto_remove=auto_remove,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party does not care about our false protocol start
        raise web.HTTPBadRequest(reason=err.roll_up)

    await outbound_handler(presentation_proposal_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_proposal_message,
        outcome="presentation_exchange_propose.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof v1.0"],
    summary="Creates a presentation request not bound to any proposal or connection",
)
@request_schema(V10PresentationCreateRequestRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200, description="")
async def presentation_exchange_create_request(request: web.BaseRequest):
    """
    Request handler for creating a free presentation request.

    The presentation request will not be bound to any proposal
    or existing connection.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile

    body = await request.json()

    comment = body.get("comment")
    indy_proof_request = body.get("proof_request")
    if not indy_proof_request.get("nonce"):
        indy_proof_request["nonce"] = await generate_pr_nonce()

    presentation_request_message = PresentationRequest(
        comment=comment,
        request_presentations_attach=[
            AttachDecorator.data_base64(
                mapping=indy_proof_request,
                ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
            )
        ],
    )
    auto_verify = body.get(
        "auto_verify", context.settings.get("debug.auto_verify_presentation")
    )
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )

    pres_ex_record = None
    try:
        presentation_manager = PresentationManager(profile)
        pres_ex_record = await presentation_manager.create_exchange_for_request(
            connection_id=None,
            presentation_request_message=presentation_request_message,
            auto_verify=auto_verify,
            auto_remove=auto_remove,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party does not care about our false protocol start
        raise web.HTTPBadRequest(reason=err.roll_up)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_create_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof v1.0"],
    summary="Sends a free presentation request not bound to any proposal",
)
@request_schema(V10PresentationSendRequestRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200, description="")
async def presentation_exchange_send_free_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request free from any proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    async with profile.session() as session:
        try:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
        except StorageNotFoundError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

    comment = body.get("comment")
    indy_proof_request = body.get("proof_request")
    if not indy_proof_request.get("nonce"):
        indy_proof_request["nonce"] = await generate_pr_nonce()

    presentation_request_message = PresentationRequest(
        comment=comment,
        request_presentations_attach=[
            AttachDecorator.data_base64(
                mapping=indy_proof_request,
                ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
            )
        ],
    )
    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    auto_verify = body.get(
        "auto_verify", context.settings.get("debug.auto_verify_presentation")
    )
    auto_remove = body.get("auto_remove")

    pres_ex_record = None
    try:
        presentation_manager = PresentationManager(profile)
        pres_ex_record = await presentation_manager.create_exchange_for_request(
            connection_id=connection_id,
            presentation_request_message=presentation_request_message,
            auto_verify=auto_verify,
            auto_remove=auto_remove,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party does not care about our false protocol start
        raise web.HTTPBadRequest(reason=err.roll_up)

    await outbound_handler(presentation_request_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof v1.0"],
    summary="Sends a presentation request in reference to a proposal",
)
@match_info_schema(V10PresExIdMatchInfoSchema())
@request_schema(V10PresentationSendRequestToProposalSchema())
@response_schema(V10PresentationExchangeSchema(), 200, description="")
async def presentation_exchange_send_bound_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request bound to a proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = None
    async with profile.session() as session:
        try:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        if pres_ex_record.state != (V10PresentationExchange.STATE_PROPOSAL_RECEIVED):
            raise web.HTTPBadRequest(
                reason=(
                    f"Presentation exchange {presentation_exchange_id} "
                    f"in {pres_ex_record.state} state "
                    f"(must be {V10PresentationExchange.STATE_PROPOSAL_RECEIVED})"
                )
            )
        conn_id = pres_ex_record.connection_id

        try:
            connection_record = await ConnRecord.retrieve_by_id(session, conn_id)
        except StorageError as err:
            raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

    pres_ex_record.auto_verify = body.get(
        "auto_verify", context.settings.get("debug.auto_verify_presentation")
    )
    pres_ex_record.auto_remove = body.get("auto_remove")

    try:
        presentation_manager = PresentationManager(profile)
        (
            pres_ex_record,
            presentation_request_message,
        ) = await presentation_manager.create_bound_request(pres_ex_record)
        result = pres_ex_record.serialize()
    except (BaseModelError, LedgerError, StorageError) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party cares that we cannot continue protocol
        await report_problem(
            err,
            ProblemReportReason.ABANDONED.value,
            web.HTTPBadRequest,
            pres_ex_record,
            outbound_handler,
        )

    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    await outbound_handler(presentation_request_message, connection_id=conn_id)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["present-proof v1.0"], summary="Sends a proof presentation")
@match_info_schema(V10PresExIdMatchInfoSchema())
@request_schema(V10PresentationSendRequestSchema())
@response_schema(V10PresentationExchangeSchema(), description="")
async def presentation_exchange_send_presentation(request: web.BaseRequest):
    """
    Request handler for sending a presentation.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]
    presentation_exchange_id = request.match_info["pres_ex_id"]
    body = await request.json()

    pres_ex_record = None
    async with profile.session() as session:
        try:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        if pres_ex_record.state != (V10PresentationExchange.STATE_REQUEST_RECEIVED):
            raise web.HTTPBadRequest(
                reason=(
                    f"Presentation exchange {presentation_exchange_id} "
                    f"in {pres_ex_record.state} state "
                    f"(must be {V10PresentationExchange.STATE_REQUEST_RECEIVED})"
                )
            )

        auto_remove = body.get("auto_remove")
        if auto_remove is None:
            auto_remove = not profile.settings.get("preserve_exchange_records")

        pres_ex_record.auto_remove = auto_remove

        # Fetch connection if exchange has record
        connection_record = None
        if pres_ex_record.connection_id:
            try:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, pres_ex_record.connection_id
                )
            except StorageNotFoundError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection_record and not connection_record.is_ready:
        raise web.HTTPForbidden(
            reason=f"Connection {connection_record.connection_id} not ready"
        )

    try:
        presentation_manager = PresentationManager(profile)
        (
            pres_ex_record,
            presentation_message,
        ) = await presentation_manager.create_presentation(
            pres_ex_record,
            {
                "self_attested_attributes": body.get("self_attested_attributes"),
                "requested_attributes": body.get("requested_attributes"),
                "requested_predicates": body.get("requested_predicates"),
            },
            comment=body.get("comment"),
        )
        result = pres_ex_record.serialize()
    except (
        BaseModelError,
        IndyHolderError,
        LedgerError,
        StorageError,
        WalletNotFoundError,
    ) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party cares that we cannot continue protocol
        await report_problem(
            err,
            ProblemReportReason.ABANDONED.value,
            web.HTTPBadRequest,
            pres_ex_record,
            outbound_handler,
        )

    trace_msg = body.get("trace")
    presentation_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    await outbound_handler(
        presentation_message, connection_id=pres_ex_record.connection_id
    )

    trace_event(
        context.settings,
        presentation_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["present-proof v1.0"], summary="Verify a received presentation")
@match_info_schema(V10PresExIdMatchInfoSchema())
@response_schema(V10PresentationExchangeSchema(), description="")
async def presentation_exchange_verify_presentation(request: web.BaseRequest):
    """
    Request handler for verifying a presentation request.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    profile = context.profile
    outbound_handler = request["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]

    pres_ex_record = None
    async with profile.session() as session:
        try:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        if pres_ex_record.state != (
            V10PresentationExchange.STATE_PRESENTATION_RECEIVED
        ):
            raise web.HTTPBadRequest(
                reason=(
                    f"Presentation exchange {presentation_exchange_id} "
                    f"in {pres_ex_record.state} state "
                    f"(must be {V10PresentationExchange.STATE_PRESENTATION_RECEIVED})"
                )
            )

    try:
        presentation_manager = PresentationManager(profile)
        pres_ex_record = await presentation_manager.verify_presentation(pres_ex_record)
        result = pres_ex_record.serialize()
    except (BaseModelError, LedgerError, StorageError) as err:
        if pres_ex_record:
            async with profile.session() as session:
                await pres_ex_record.save_error_state(session, reason=err.roll_up)
        # other party cares that we cannot continue protocol
        await report_problem(
            err,
            ProblemReportReason.ABANDONED.value,
            web.HTTPBadRequest,
            pres_ex_record,
            outbound_handler,
        )
    except PresentationManagerError as err:
        return web.HTTPBadRequest(reason=err.roll_up)

    trace_event(
        context.settings,
        pres_ex_record,
        outcome="presentation_exchange_verify.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof v1.0"],
    summary="Send a problem report for presentation exchange",
)
@match_info_schema(V10PresExIdMatchInfoSchema())
@request_schema(V10PresentationProblemReportRequestSchema())
@response_schema(V10PresentProofModuleResponseSchema(), 200, description="")
async def presentation_exchange_problem_report(request: web.BaseRequest):
    """
    Request handler for sending problem report.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    pres_ex_id = request.match_info["pres_ex_id"]
    body = await request.json()
    description = body["description"]

    try:
        async with await context.profile.session() as session:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, pres_ex_id
            )
            report = problem_report_for_record(pres_ex_record, description)
            await pres_ex_record.save_error_state(
                session,
                reason=f"created problem report: {description}",
            )
    except StorageNotFoundError as err:  # other party does not care about meta-problems
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    await outbound_handler(report, connection_id=pres_ex_record.connection_id)

    return web.json_response({})


@docs(
    tags=["present-proof v1.0"],
    summary="Remove an existing presentation exchange record",
)
@match_info_schema(V10PresExIdMatchInfoSchema())
@response_schema(V10PresentProofModuleResponseSchema(), description="")
async def presentation_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a presentation exchange record.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = None
    try:
        async with context.profile.session() as session:
            pres_ex_record = await V10PresentationExchange.retrieve_by_id(
                session, presentation_exchange_id
            )
            await pres_ex_record.delete_record(session)
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/present-proof/records",
                presentation_exchange_list,
                allow_head=False,
            ),
            web.get(
                "/present-proof/records/{pres_ex_id}",
                presentation_exchange_retrieve,
                allow_head=False,
            ),
            web.get(
                "/present-proof/records/{pres_ex_id}/credentials",
                presentation_exchange_credentials_list,
                allow_head=False,
            ),
            web.post(
                "/present-proof/send-proposal",
                presentation_exchange_send_proposal,
            ),
            web.post(
                "/present-proof/create-request",
                presentation_exchange_create_request,
            ),
            web.post(
                "/present-proof/send-request",
                presentation_exchange_send_free_request,
            ),
            web.post(
                "/present-proof/records/{pres_ex_id}/send-request",
                presentation_exchange_send_bound_request,
            ),
            web.post(
                "/present-proof/records/{pres_ex_id}/send-presentation",
                presentation_exchange_send_presentation,
            ),
            web.post(
                "/present-proof/records/{pres_ex_id}/verify-presentation",
                presentation_exchange_verify_presentation,
            ),
            web.post(
                "/present-proof/records/{pres_ex_id}/problem-report",
                presentation_exchange_problem_report,
            ),
            web.delete(
                "/present-proof/records/{pres_ex_id}",
                presentation_exchange_remove,
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
            "name": "present-proof v1.0",
            "description": "Proof presentation v1.0",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
