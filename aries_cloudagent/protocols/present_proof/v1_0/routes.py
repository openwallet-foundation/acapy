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
from marshmallow import fields, validate, validates_schema
from marshmallow.exceptions import ValidationError

from ....connections.models.connection_record import ConnectionRecord
from ....holder.base import BaseHolder, HolderError
from ....indy.util import generate_pr_nonce
from ....ledger.error import LedgerError
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.models.base import BaseModelError
from ....messaging.models.openapi import OpenAPISchema
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_EXTRA_WQL,
    INDY_PREDICATE,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    INT_EPOCH,
    NATURAL_NUM,
    UUIDFour,
    UUID4,
    WHOLE_NUM,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....utils.tracing import trace_event, get_timer, AdminAPIMessageTracingSchema
from ....wallet.error import WalletNotFoundError

from ...problem_report.v1_0 import internal_error

from .manager import PresentationManager
from .message_types import ATTACH_DECO_IDS, PRESENTATION_REQUEST, SPEC_URI
from .messages.inner.presentation_preview import (
    PresentationPreview,
    PresentationPreviewSchema,
)
from .messages.presentation_proposal import PresentationProposal
from .messages.presentation_request import PresentationRequest
from .models.presentation_exchange import (
    V10PresentationExchange,
    V10PresentationExchangeSchema,
)


class V10PresentationExchangeListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for presentation exchange list query."""

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
        description="Role assigned in presentation exchange",
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10PresentationExchange, m)
                for m in vars(V10PresentationExchange)
                if m.startswith("ROLE_")
            ]
        ),
    )
    state = fields.Str(
        description="Presentation exchange state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(V10PresentationExchange, m)
                for m in vars(V10PresentationExchange)
                if m.startswith("STATE_")
            ]
        ),
    )


class V10PresentationExchangeListSchema(OpenAPISchema):
    """Result schema for an Aries RFC 37 v1.0 presentation exchange query."""

    results = fields.List(
        fields.Nested(V10PresentationExchangeSchema()),
        description="Aries RFC 37 v1.0 presentation exchange records",
    )


class V10PresentationProposalRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for sending a presentation proposal admin message."""

    connection_id = fields.UUID(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )
    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )
    presentation_proposal = fields.Nested(PresentationPreviewSchema(), required=True)
    auto_present = fields.Boolean(
        description=(
            "Whether to respond automatically to presentation requests, building "
            "and presenting requested proof"
        ),
        required=False,
        default=False,
    )
    trace = fields.Bool(
        description="Whether to trace event (default false)",
        required=False,
        example=False,
    )


class IndyProofReqPredSpecRestrictionsSchema(OpenAPISchema):
    """Schema for restrictions in attr or pred specifier indy proof request."""

    schema_id = fields.String(
        description="Schema identifier", required=False, **INDY_SCHEMA_ID
    )
    schema_issuer_did = fields.String(
        description="Schema issuer (origin) DID", required=False, **INDY_DID
    )
    schema_name = fields.String(
        example="transcript", description="Schema name", required=False
    )
    schema_version = fields.String(
        description="Schema version", required=False, **INDY_VERSION
    )
    issuer_did = fields.String(
        description="Credential issuer DID", required=False, **INDY_DID
    )
    cred_def_id = fields.String(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )


class IndyProofReqNonRevokedSchema(OpenAPISchema):
    """Non-revocation times specification in indy proof request."""

    fro = fields.Int(
        description="Earliest epoch of interest for non-revocation proof",
        required=False,
        data_key="from",
        **INT_EPOCH,
    )
    to = fields.Int(
        description="Latest epoch of interest for non-revocation proof",
        required=False,
        **INT_EPOCH,
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields - must have from, to, or both.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has neither from nor to

        """
        if not (data.get("from") or data.get("to")):
            raise ValidationError(
                "Non-revocation interval must have at least one end", ("fro", "to")
            )


class IndyProofReqAttrSpecSchema(OpenAPISchema):
    """Schema for attribute specification in indy proof request."""

    name = fields.String(
        example="favouriteDrink", description="Attribute name", required=False
    )
    names = fields.List(
        fields.String(example="age"),
        description="Attribute name group",
        required=False,
    )
    restrictions = fields.List(
        fields.Dict(
            keys=fields.Str(
                validate=validate.Regexp(
                    "^schema_id|"
                    "schema_issuer_did|"
                    "schema_name|"
                    "schema_version|"
                    "issuer_did|"
                    "cred_def_id|"
                    "attr::.+::value$"  # indy does not support attr::...::marker here
                ),
                example="cred_def_id",  # marshmallow/apispec v3.0 ignores
            ),
            values=fields.Str(example=INDY_CRED_DEF_ID["example"]),
        ),
        description=(
            "If present, credential must satisfy one of given restrictions: specify "
            "schema_id, schema_issuer_did, schema_name, schema_version, "
            "issuer_did, cred_def_id, and/or attr::<attribute-name>::value "
            "where <attribute-name> represents a credential attribute name"
        ),
        required=False,
    )
    non_revoked = fields.Nested(IndyProofReqNonRevokedSchema(), required=False)

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Data must have exactly one of name or names; if names then restrictions are
        mandatory.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has both or neither of name and names

        """
        if ("name" in data) == ("names" in data):
            raise ValidationError(
                "Attribute specification must have either name or names but not both"
            )
        restrictions = data.get("restrictions")
        if ("names" in data) and (not restrictions or all(not r for r in restrictions)):
            raise ValidationError(
                "Attribute specification on 'names' must have non-empty restrictions"
            )


class IndyProofReqPredSpecSchema(OpenAPISchema):
    """Schema for predicate specification in indy proof request."""

    name = fields.String(example="index", description="Attribute name", required=True)
    p_type = fields.String(
        description="Predicate type ('<', '<=', '>=', or '>')",
        required=True,
        **INDY_PREDICATE,
    )
    p_value = fields.Integer(description="Threshold value", required=True)
    restrictions = fields.List(
        fields.Nested(IndyProofReqPredSpecRestrictionsSchema()),
        description="If present, credential must satisfy one of given restrictions",
        required=False,
    )
    non_revoked = fields.Nested(IndyProofReqNonRevokedSchema(), required=False)


class IndyProofRequestSchema(OpenAPISchema):
    """Schema for indy proof request."""

    nonce = fields.String(description="Nonce", required=False, example="1234567890")
    name = fields.String(
        description="Proof request name",
        required=False,
        example="Proof request",
        default="Proof request",
    )
    version = fields.String(
        description="Proof request version",
        required=False,
        default="1.0",
        **INDY_VERSION,
    )
    requested_attributes = fields.Dict(
        description=("Requested attribute specifications of proof request"),
        required=True,
        keys=fields.Str(example="0_attr_uuid"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyProofReqAttrSpecSchema()),
    )
    requested_predicates = fields.Dict(
        description=("Requested predicate specifications of proof request"),
        required=True,
        keys=fields.Str(example="0_age_GE_uuid"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyProofReqPredSpecSchema()),
    )
    non_revoked = fields.Nested(IndyProofReqNonRevokedSchema(), required=False)


class V10PresentationCreateRequestRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for creating a proof request free of any connection."""

    proof_request = fields.Nested(IndyProofRequestSchema(), required=True)
    comment = fields.Str(required=False, allow_none=True)
    trace = fields.Bool(
        description="Whether to trace event (default false)",
        required=False,
        example=False,
    )


class V10PresentationSendRequestRequestSchema(
    V10PresentationCreateRequestRequestSchema
):
    """Request schema for sending a proof request on a connection."""

    connection_id = fields.UUID(
        description="Connection identifier", required=True, example=UUIDFour.EXAMPLE
    )


class IndyRequestedCredsRequestedAttrSchema(OpenAPISchema):
    """Schema for requested attributes within indy requested credentials structure."""

    cred_id = fields.Str(
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        description=(
            "Wallet credential identifier (typically but not necessarily a UUID)"
        ),
        required=True,
    )
    revealed = fields.Bool(
        description="Whether to reveal attribute in proof", required=True
    )
    timestamp = fields.Int(
        description="Epoch timestamp of interest for non-revocation proof",
        required=False,
        **INT_EPOCH,
    )


class IndyRequestedCredsRequestedPredSchema(OpenAPISchema):
    """Schema for requested predicates within indy requested credentials structure."""

    cred_id = fields.Str(
        description=(
            "Wallet credential identifier (typically but not necessarily a UUID)"
        ),
        example="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        required=True,
    )
    timestamp = fields.Int(
        description="Epoch timestamp of interest for non-revocation proof",
        required=False,
        **INT_EPOCH,
    )


class V10PresentationRequestSchema(AdminAPIMessageTracingSchema):
    """Request schema for sending a presentation."""

    self_attested_attributes = fields.Dict(
        description=("Self-attested attributes to build into proof"),
        required=True,
        keys=fields.Str(example="attr_name"),  # marshmallow/apispec v3.0 ignores
        values=fields.Str(
            example="self_attested_value",
            description=(
                "Self-attested attribute values to use in requested-credentials "
                "structure for proof construction"
            ),
        ),
    )
    requested_attributes = fields.Dict(
        description=(
            "Nested object mapping proof request attribute referents to "
            "requested-attribute specifiers"
        ),
        required=True,
        keys=fields.Str(example="attr_referent"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyRequestedCredsRequestedAttrSchema()),
    )
    requested_predicates = fields.Dict(
        description=(
            "Nested object mapping proof request predicate referents to "
            "requested-predicate specifiers"
        ),
        required=True,
        keys=fields.Str(example="pred_referent"),  # marshmallow/apispec v3.0 ignores
        values=fields.Nested(IndyRequestedCredsRequestedPredSchema()),
    )
    trace = fields.Bool(
        description="Whether to trace event (default false)",
        required=False,
        example=False,
    )


class CredentialsFetchQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credentials fetch request query string."""

    referent = fields.Str(
        description="Proof request referents of interest, comma-separated",
        required=False,
        example="1_name_uuid,2_score_uuid",
    )
    start = fields.Int(description="Start index", required=False, **WHOLE_NUM)
    count = fields.Int(
        description="Maximum number to retrieve", required=False, **NATURAL_NUM
    )
    extra_query = fields.Str(
        description="(JSON) object mapping referents to extra WQL queries",
        required=False,
        **INDY_EXTRA_WQL,
    )


class PresExIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking presentation exchange id."""

    pres_ex_id = fields.Str(
        description="Presentation exchange identifier", required=True, **UUID4
    )


@docs(tags=["present-proof"], summary="Fetch all present-proof exchange records")
@querystring_schema(V10PresentationExchangeListQueryStringSchema)
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
    if "thread_id" in request.query and request.query["thread_id"] != "":
        tag_filter["thread_id"] = request.query["thread_id"]
    post_filter = {
        k: request.query[k]
        for k in ("connection_id", "role", "state")
        if request.query.get(k, "") != ""
    }

    try:
        records = await V10PresentationExchange.query(context, tag_filter, post_filter)
        results = [record.serialize() for record in records]
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(tags=["present-proof"], summary="Fetch a single presentation exchange record")
@match_info_schema(PresExIdMatchInfoSchema())
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
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = None
    try:
        pres_ex_record = await V10PresentationExchange.retrieve_by_id(
            context, presentation_exchange_id
        )
        result = pres_ex_record.serialize()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, pres_ex_record, outbound_handler)

    return web.json_response(result)


@docs(
    tags=["present-proof"],
    summary="Fetch credentials for a presentation request from wallet",
)
@match_info_schema(PresExIdMatchInfoSchema())
@querystring_schema(CredentialsFetchQueryStringSchema())
async def presentation_exchange_credentials_list(request: web.BaseRequest):
    """
    Request handler for searching applicable credential records.

    Args:
        request: aiohttp request object

    Returns:
        The credential list response

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    referents = request.query.get("referent")
    presentation_referents = (
        (r.strip() for r in referents.split(",")) if referents else ()
    )

    try:
        pres_ex_record = await V10PresentationExchange.retrieve_by_id(
            context, presentation_exchange_id
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

    holder: BaseHolder = await context.inject(BaseHolder)
    try:
        credentials = await holder.get_credentials_for_presentation_request_by_referent(
            pres_ex_record.presentation_request,
            presentation_referents,
            start,
            count,
            extra_query,
        )
    except HolderError as err:
        await internal_error(err, web.HTTPBadRequest, pres_ex_record, outbound_handler)

    pres_ex_record.log_state(
        context,
        "Retrieved presentation credentials",
        {
            "presentation_exchange_id": presentation_exchange_id,
            "referents": presentation_referents,
            "extra_query": extra_query,
            "credentials": credentials,
        },
    )
    return web.json_response(credentials)


@docs(tags=["present-proof"], summary="Sends a presentation proposal")
@request_schema(V10PresentationProposalRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200)
async def presentation_exchange_send_proposal(request: web.BaseRequest):
    """
    Request handler for sending a presentation proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    connection_id = body.get("connection_id")

    # Aries RFC 37 calls it a proposal in the proposal struct but it's of type preview
    presentation_preview = body.get("presentation_proposal")
    connection_record = None
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
        presentation_proposal_message = PresentationProposal(
            comment=comment,
            presentation_proposal=PresentationPreview.deserialize(presentation_preview),
        )
    except (BaseModelError, StorageError) as err:
        await internal_error(
            err, web.HTTPBadRequest, connection_record, outbound_handler
        )

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

    presentation_manager = PresentationManager(context)
    pres_ex_record = None
    try:
        pres_ex_record = await presentation_manager.create_exchange_for_proposal(
            connection_id=connection_id,
            presentation_proposal_message=presentation_proposal_message,
            auto_present=auto_present,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            pres_ex_record or connection_record,
            outbound_handler,
        )

    await outbound_handler(presentation_proposal_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_proposal_message,
        outcome="presentation_exchange_propose.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof"],
    summary="""
    Creates a presentation request not bound to any proposal or existing connection
    """,
)
@request_schema(V10PresentationCreateRequestRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200)
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

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    indy_proof_request = body.get("proof_request")
    if not indy_proof_request.get("nonce"):
        indy_proof_request["nonce"] = await generate_pr_nonce()

    presentation_request_message = PresentationRequest(
        comment=comment,
        request_presentations_attach=[
            AttachDecorator.from_indy_dict(
                indy_dict=indy_proof_request,
                ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
            )
        ],
    )
    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )

    presentation_manager = PresentationManager(context)
    pres_ex_record = None
    try:
        (pres_ex_record) = await presentation_manager.create_exchange_for_request(
            connection_id=None,
            presentation_request_message=presentation_request_message,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, pres_ex_record, outbound_handler)

    await outbound_handler(presentation_request_message, connection_id=None)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_create_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof"],
    summary="Sends a free presentation request not bound to any proposal",
)
@request_schema(V10PresentationSendRequestRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200)
async def presentation_exchange_send_free_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request free from any proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()

    connection_id = body.get("connection_id")
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
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
            AttachDecorator.from_indy_dict(
                indy_dict=indy_proof_request,
                ident=ATTACH_DECO_IDS[PRESENTATION_REQUEST],
            )
        ],
    )
    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )

    presentation_manager = PresentationManager(context)
    pres_ex_record = None
    try:
        (pres_ex_record) = await presentation_manager.create_exchange_for_request(
            connection_id=connection_id,
            presentation_request_message=presentation_request_message,
        )
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            pres_ex_record or connection_record,
            outbound_handler,
        )

    await outbound_handler(presentation_request_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["present-proof"],
    summary="Sends a presentation request in reference to a proposal",
)
@match_info_schema(PresExIdMatchInfoSchema())
@request_schema(V10PresentationSendRequestRequestSchema())
@response_schema(V10PresentationExchangeSchema(), 200)
async def presentation_exchange_send_bound_request(request: web.BaseRequest):
    """
    Request handler for sending a presentation request free from any proposal.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = await V10PresentationExchange.retrieve_by_id(
        context, presentation_exchange_id
    )
    if pres_ex_record.state != (V10PresentationExchange.STATE_PROPOSAL_RECEIVED):
        raise web.HTTPBadRequest(
            reason=(
                f"Presentation exchange {presentation_exchange_id} "
                f"in {pres_ex_record.state} state "
                f"(must be {V10PresentationExchange.STATE_PROPOSAL_RECEIVED})"
            )
        )
    body = await request.json()

    connection_id = body.get("connection_id")
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

    presentation_manager = PresentationManager(context)
    try:
        (
            pres_ex_record,
            presentation_request_message,
        ) = await presentation_manager.create_bound_request(pres_ex_record)
        result = pres_ex_record.serialize()
    except (BaseModelError, StorageError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            pres_ex_record or connection_record,
            outbound_handler,
        )

    trace_msg = body.get("trace")
    presentation_request_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    await outbound_handler(presentation_request_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_request_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["present-proof"], summary="Sends a proof presentation")
@match_info_schema(PresExIdMatchInfoSchema())
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
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]
    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = await V10PresentationExchange.retrieve_by_id(
        context, presentation_exchange_id
    )
    if pres_ex_record.state != (V10PresentationExchange.STATE_REQUEST_RECEIVED):
        raise web.HTTPBadRequest(
            reason=(
                f"Presentation exchange {presentation_exchange_id} "
                f"in {pres_ex_record.state} state "
                f"(must be {V10PresentationExchange.STATE_REQUEST_RECEIVED})"
            )
        )

    body = await request.json()

    connection_id = pres_ex_record.connection_id
    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageNotFoundError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

    presentation_manager = PresentationManager(context)
    try:
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
        HolderError,
        LedgerError,
        StorageError,
        WalletNotFoundError,
    ) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            pres_ex_record or connection_record,
            outbound_handler,
        )

    trace_msg = body.get("trace")
    presentation_message.assign_trace_decorator(
        context.settings,
        trace_msg,
    )
    await outbound_handler(presentation_message, connection_id=connection_id)

    trace_event(
        context.settings,
        presentation_message,
        outcome="presentation_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["present-proof"], summary="Verify a received presentation")
@match_info_schema(PresExIdMatchInfoSchema())
@response_schema(V10PresentationExchangeSchema())
async def presentation_exchange_verify_presentation(request: web.BaseRequest):
    """
    Request handler for verifying a presentation request.

    Args:
        request: aiohttp request object

    Returns:
        The presentation exchange details

    """
    r_time = get_timer()

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]

    pres_ex_record = await V10PresentationExchange.retrieve_by_id(
        context, presentation_exchange_id
    )
    if pres_ex_record.state != (V10PresentationExchange.STATE_PRESENTATION_RECEIVED):
        raise web.HTTPBadRequest(
            reason=(
                f"Presentation exchange {presentation_exchange_id} "
                f"in {pres_ex_record.state} state "
                f"(must be {V10PresentationExchange.STATE_PRESENTATION_RECEIVED})"
            )
        )

    connection_id = pres_ex_record.connection_id

    try:
        connection_record = await ConnectionRecord.retrieve_by_id(
            context, connection_id
        )
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if not connection_record.is_ready:
        raise web.HTTPForbidden(reason=f"Connection {connection_id} not ready")

    presentation_manager = PresentationManager(context)
    try:
        pres_ex_record = await presentation_manager.verify_presentation(pres_ex_record)
        result = pres_ex_record.serialize()
    except (LedgerError, BaseModelError) as err:
        await internal_error(err, web.HTTPBadRequest, pres_ex_record, outbound_handler)

    trace_event(
        context.settings,
        pres_ex_record,
        outcome="presentation_exchange_verify.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(tags=["present-proof"], summary="Remove an existing presentation exchange record")
@match_info_schema(PresExIdMatchInfoSchema())
async def presentation_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a presentation exchange record.

    Args:
        request: aiohttp request object

    """
    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    presentation_exchange_id = request.match_info["pres_ex_id"]
    pres_ex_record = None
    try:
        pres_ex_record = await V10PresentationExchange.retrieve_by_id(
            context, presentation_exchange_id
        )
        await pres_ex_record.delete_record(context)
    except StorageNotFoundError as err:
        await internal_error(err, web.HTTPNotFound, pres_ex_record, outbound_handler)
    except StorageError as err:
        await internal_error(err, web.HTTPBadRequest, pres_ex_record, outbound_handler)

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/present-proof/records", presentation_exchange_list, allow_head=False
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
                "/present-proof/records/{pres_ex_id}/remove",
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
            "name": "present-proof",
            "description": "Proof presentation",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
