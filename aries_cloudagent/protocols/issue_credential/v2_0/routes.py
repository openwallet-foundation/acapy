"""Credential exchange admin routes."""

from json.decoder import JSONDecodeError
from typing import Mapping

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate, validates_schema, ValidationError

from ....admin.request_context import AdminRequestContext
from ....connections.models.conn_record import ConnRecord
from ....core.profile import Profile
from ....indy.issuer import IndyIssuerError
from ....ledger.error import LedgerError
from ....messaging.decorators.attach_decorator import AttachDecorator
from ....messaging.models.base import BaseModelError, OpenAPISchema
from ....messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_DID,
    INDY_SCHEMA_ID,
    INDY_VERSION,
    UUIDFour,
    UUID4,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....wallet.base import BaseWallet
from ....wallet.error import WalletError
from ....utils.outofband import serialize_outofband
from ....utils.tracing import trace_event, get_timer, AdminAPIMessageTracingSchema

from ...problem_report.v1_0 import internal_error
from ...problem_report.v1_0.message import ProblemReport

from .manager import V20CredManager, V20CredManagerError
from .message_types import SPEC_URI
from .messages.cred_format import V20CredFormat
from .messages.cred_offer import V20CredOfferSchema
from .messages.cred_proposal import V20CredProposal
from .messages.inner.cred_preview import V20CredPreview, V20CredPreviewSchema
from .models.cred_ex_record import V20CredExRecord, V20CredExRecordSchema
from .models.detail.dif import V20CredExRecordDIFSchema
from .models.detail.indy import V20CredExRecordIndySchema


class V20IssueCredentialModuleResponseSchema(OpenAPISchema):
    """Response schema for v2.0 Issue Credential Module."""


class V20CredExRecordListQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential exchange record list query."""

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
                getattr(V20CredExRecord, m)
                for m in vars(V20CredExRecord)
                if m.startswith("ROLE_")
            ]
        ),
    )
    state = fields.Str(
        description="Credential exchange state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(V20CredExRecord, m)
                for m in vars(V20CredExRecord)
                if m.startswith("STATE_")
            ]
        ),
    )


class V20CredExRecordDetailSchema(OpenAPISchema):
    """Credential exchange record and any per-format details."""

    cred_ex_record = fields.Nested(
        V20CredExRecordSchema,
        required=False,
        description="Credential exchange record",
    )
    indy = fields.Nested(
        V20CredExRecordIndySchema,
        required=False,
    )
    dif = fields.Nested(
        V20CredExRecordDIFSchema,
        required=False,
    )


class V20CredExRecordListResultSchema(OpenAPISchema):
    """Result schema for credential exchange record list query."""

    results = fields.List(
        fields.Nested(V20CredExRecordDetailSchema),
        description="Credential exchange records and corresponding detail records",
    )


class V20CredStoreRequestSchema(OpenAPISchema):
    """Request schema for sending a credential store admin message."""

    credential_id = fields.Str(required=False)


class V20CredFilterIndy(OpenAPISchema):
    """Indy credential filtration criteria."""

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


class V20CredFilterDIF(OpenAPISchema):
    """DIF credential filtration criteria."""

    some_dif_criterion = fields.Str(
        description="Placeholder for W3C/DIF/JSON-LD filtration criterion",
        required=False,
    )


class V20CredFilter(OpenAPISchema):
    """Credential filtration criteria."""

    indy = fields.Nested(
        V20CredFilterIndy, required=False, description="Credential filter for indy"
    )
    dif = fields.Nested(
        V20CredFilterDIF, required=False, description="Credential filter for DIF"
    )

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """
        Validate schema fields.

        Data must have indy, dif, or both.

        Args:
            data: The data to validate

        Raises:
            ValidationError: if data has neither indy nor dif

        """
        if not (("indy" in data) or ("dif" in data)):
            raise ValidationError("V20CredFilter requires indy, dif, or both")


class V20IssueCredSchemaCore(AdminAPIMessageTracingSchema):
    """Filter, auto-remove, comment, trace."""

    filter_ = fields.Nested(
        V20CredFilter,
        required=True,
        data_key="filter",
        description="Credential specification criteria by format",
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
    trace = fields.Bool(
        description="Whether to trace event (default false)",
        required=False,
        example=False,
    )


class V20CredCreateSchema(V20IssueCredSchemaCore):
    """Request schema for creating a credential from attr values."""

    credential_preview = fields.Nested(V20CredPreviewSchema, required=True)


class V20CredProposalRequestSchemaBase(V20IssueCredSchemaCore):
    """Base class for request schema for sending credential proposal admin message."""

    connection_id = fields.UUID(
        description="Connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )


class V20CredProposalRequestPreviewOptSchema(V20CredProposalRequestSchemaBase):
    """Request schema for sending credential proposal on optional proposal preview."""

    credential_preview = fields.Nested(V20CredPreviewSchema, required=False)


class V20CredProposalRequestPreviewMandSchema(V20CredProposalRequestSchemaBase):
    """Request schema for sending credential proposal on mandatory proposal preview."""

    credential_preview = fields.Nested(V20CredPreviewSchema, required=True)


class V20CredOfferRequestSchema(V20IssueCredSchemaCore):
    """Request schema for sending credential offer admin message."""

    connection_id = fields.UUID(
        description="Connection identifier",
        required=True,
        example=UUIDFour.EXAMPLE,  # typically but not necessarily a UUID4
    )
    auto_issue = fields.Bool(
        description=(
            "Whether to respond automatically to credential requests, creating "
            "and issuing requested credentials"
        ),
        required=False,
    )
    credential_preview = fields.Nested(V20CredPreviewSchema, required=True)


class V20CredIssueRequestSchema(OpenAPISchema):
    """Request schema for sending credential issue admin message."""

    comment = fields.Str(
        description="Human-readable comment", required=False, allow_none=True
    )


class V20CredIssueProblemReportRequestSchema(OpenAPISchema):
    """Request schema for sending problem report."""

    explain_ltxt = fields.Str(required=True)


class V20CredIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential id."""

    credential_id = fields.Str(
        description="Credential identifier", required=True, example=UUIDFour.EXAMPLE
    )


class V20CredExIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking credential exchange id."""

    cred_ex_id = fields.Str(
        description="Credential exchange identifier", required=True, **UUID4
    )


def _formats_filters(filt_spec: Mapping) -> Mapping:
    """Break out formats and filters for v2.0 messages."""

    return {
        "formats": [
            V20CredFormat(
                attach_id=fmt_aka,
                format_=V20CredFormat.Format.get(fmt_aka),
            )
            for fmt_aka in filt_spec.keys()
        ],
        "filters_attach": [
            AttachDecorator.data_base64(filt_by_fmt, ident=fmt_aka)
            for (fmt_aka, filt_by_fmt) in filt_spec.items()
        ],
    }


@docs(
    tags=["issue-credential v2.0"],
    summary="Fetch all credential exchange records",
)
@querystring_schema(V20CredExRecordListQueryStringSchema)
@response_schema(V20CredExRecordListResultSchema(), 200, description="")
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
        async with context.session() as session:
            cred_ex_records = await V20CredExRecord.query(
                session=session,
                tag_filter=tag_filter,
                post_filter_positive=post_filter,
            )

        results = []
        cred_manager = V20CredManager(context.profile)
        for cxr in cred_ex_records:
            indy_record = await cred_manager.get_detail_record(
                cxr.cred_ex_id,
                V20CredFormat.Format.INDY,
            )
            dif_record = await cred_manager.get_detail_record(
                cxr.cred_ex_id,
                V20CredFormat.Format.DIF,
            )
            results.append(
                {
                    "cred_ex_record": cxr.serialize(),
                    "indy": indy_record.serialize() if indy_record else None,
                    "dif": dif_record.serialize() if dif_record else None,
                }
            )

    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"results": results})


@docs(
    tags=["issue-credential v2.0"],
    summary="Fetch a single credential exchange record",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@response_schema(V20CredExRecordDetailSchema(), 200, description="")
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

    cred_ex_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    try:
        async with context.session() as session:
            cred_ex_record = await V20CredExRecord.retrieve_by_id(session, cred_ex_id)

        cred_manager = V20CredManager(context.profile)
        indy_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.INDY
        )
        dif_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.DIF
        )
        result = {
            "cred_ex_record": cred_ex_record.serialize(),
            "indy": indy_record.serialize() if indy_record else None,
            "dif": dif_record.serialize() if dif_record else None,
        }

    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except (BaseModelError, StorageError) as err:
        await internal_error(err, web.HTTPBadRequest, cred_ex_record, outbound_handler)

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send holder a credential, automating entire flow",
)
@request_schema(V20CredCreateSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    preview_spec = body.get("credential_preview")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="Missing credential_preview")
    auto_remove = body.get("auto_remove")
    filt_spec = body.get("filter")
    if not filt_spec:
        raise web.HTTPBadRequest(reason="Missing filter")
    trace_msg = body.get("trace")

    try:
        cred_preview = V20CredPreview.deserialize(preview_spec)
        cred_proposal = V20CredProposal(
            comment=comment,
            credential_preview=cred_preview,
            **_formats_filters(filt_spec),
        )
        cred_proposal.assign_trace_decorator(
            context.settings,
            trace_msg,
        )

        trace_event(
            context.settings,
            cred_proposal,
            outcome="credential_exchange_create.START",
        )

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_offer_message) = await cred_manager.prepare_send(
            conn_id=None,
            cred_proposal=cred_proposal,
            auto_remove=auto_remove,
        )
    except (StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    trace_event(
        context.settings,
        cred_offer_message,
        outcome="credential_exchange_create.END",
        perf_counter=r_time,
    )

    return web.json_response(cred_ex_record.serialize())


@docs(
    tags=["issue-credential v2.0"],
    summary="Send holder a credential, automating entire flow",
)
@request_schema(V20CredProposalRequestPreviewMandSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    comment = body.get("comment")
    conn_id = body.get("connection_id")
    preview_spec = body.get("credential_preview")
    if not preview_spec:
        raise web.HTTPBadRequest(reason="Missing credential_preview")
    filt_spec = body.get("filter")
    if not filt_spec:
        raise web.HTTPBadRequest(reason="Missing filter")
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")

    conn_record = None
    cred_ex_record = None
    try:
        cred_preview = V20CredPreview.deserialize(preview_spec)
        async with context.session() as session:
            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_proposal = V20CredProposal(
            comment=comment,
            credential_preview=cred_preview,
            **_formats_filters(filt_spec),
        )
        cred_proposal.assign_trace_decorator(
            context.settings,
            trace_msg,
        )

        trace_event(
            context.settings,
            cred_proposal,
            outcome="credential_exchange_send.START",
        )

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_offer_message) = await cred_manager.prepare_send(
            conn_id,
            cred_proposal=cred_proposal,
            auto_remove=auto_remove,
        )
        result = cred_ex_record.serialize()

    except (StorageError, BaseModelError, V20CredManagerError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_offer_message, connection_id=cred_ex_record.conn_id)

    trace_event(
        context.settings,
        cred_offer_message,
        outcome="credential_exchange_send.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send issuer a credential proposal",
)
@request_schema(V20CredProposalRequestPreviewOptSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    conn_id = body.get("connection_id")
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")
    filt_spec = body.get("filter")
    if not filt_spec:
        raise web.HTTPBadRequest(reason="Missing filter")
    auto_remove = body.get("auto_remove")
    trace_msg = body.get("trace")

    conn_record = None
    cred_ex_record = None
    try:
        cred_preview = (
            V20CredPreview.deserialize(preview_spec) if preview_spec else None
        )
        async with context.session() as session:
            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_manager = V20CredManager(context.profile)
        cred_ex_record = await cred_manager.create_proposal(
            conn_id=conn_id,
            auto_remove=auto_remove,
            comment=comment,
            cred_preview=cred_preview,
            trace=trace_msg,
            fmt2filter={
                V20CredFormat.Format.get(fmt_aka): filt_by_fmt
                for (fmt_aka, filt_by_fmt) in filt_spec.items()
            },
        )

        cred_proposal_message = V20CredProposal.deserialize(
            cred_ex_record.cred_proposal
        )
        result = cred_ex_record.serialize()

    except (BaseModelError, StorageError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_proposal_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_proposal_message,
        outcome="credential_exchange_send_proposal.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


async def _create_free_offer(
    profile: Profile,
    filt_spec: Mapping = None,
    conn_id: str = None,
    auto_issue: bool = False,
    auto_remove: bool = False,
    preview_spec: dict = None,
    comment: str = None,
    trace_msg: bool = None,
):
    """Create a credential offer and related exchange record."""

    cred_preview = V20CredPreview.deserialize(preview_spec)
    cred_proposal = V20CredProposal(
        comment=comment,
        credential_preview=cred_preview,
        **_formats_filters(filt_spec),
    )
    cred_proposal.assign_trace_decorator(
        profile.settings,
        trace_msg,
    )

    cred_ex_record = V20CredExRecord(
        conn_id=conn_id,
        initiator=V20CredExRecord.INITIATOR_SELF,
        role=V20CredExRecord.ROLE_ISSUER,
        cred_proposal=cred_proposal.serialize(),
        auto_issue=auto_issue,
        auto_remove=auto_remove,
        trace=trace_msg,
    )

    cred_manager = V20CredManager(profile)
    (cred_ex_record, cred_offer_message) = await cred_manager.create_offer(
        cred_ex_record,
        comment=comment,
    )

    return (cred_ex_record, cred_offer_message)


@docs(
    tags=["issue-credential v2.0"],
    summary="Create a credential offer, independent of any proposal",
)
@request_schema(V20CredOfferRequestSchema())
@response_schema(V20CredOfferSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    auto_issue = body.get(
        "auto_issue", context.settings.get("debug.auto_respond_credential_request")
    )
    auto_remove = body.get("auto_remove")
    comment = body.get("comment")
    preview_spec = body.get("credential_preview")
    if not preview_spec:
        raise web.HTTPBadRequest(reason=("Missing credential_preview"))
    filt_spec = body.get("filter")
    if not filt_spec:
        raise web.HTTPBadRequest(reason="Missing filter")
    conn_id = body.get("connection_id")
    trace_msg = body.get("trace")

    async with context.session() as session:
        wallet = session.inject(BaseWallet)
        if conn_id:
            try:
                conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
                conn_did = await wallet.get_local_did(conn_record.my_did)
            except (WalletError, StorageError) as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err
        else:
            conn_did = await wallet.get_public_did()
            if not conn_did:
                raise web.HTTPBadRequest(reason="Wallet has no public DID")
            conn_id = None

        did_info = await wallet.get_public_did()
        del wallet

    endpoint = did_info.metadata.get(
        "endpoint", context.settings.get("default_endpoint")
    )
    if not endpoint:
        raise web.HTTPBadRequest(reason="An endpoint for the public DID is required")

    cred_ex_record = None
    try:
        (cred_ex_record, cred_offer_message) = await _create_free_offer(
            context.profile,
            filt_spec,
            conn_id,
            auto_issue,
            auto_remove,
            preview_spec,
            comment,
            trace_msg,
        )

        trace_event(
            context.settings,
            cred_offer_message,
            outcome="credential_exchange_create_free_offer.END",
            perf_counter=r_time,
        )

        oob_url = serialize_outofband(cred_offer_message, conn_did, endpoint)
        result = cred_ex_record.serialize()

    except (BaseModelError, V20CredManagerError, LedgerError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    response = {"record": result, "oob_url": oob_url}
    return web.json_response(response)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send holder a credential offer, independent of any proposal",
)
@request_schema(V20CredOfferRequestSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    body = await request.json()

    conn_id = body.get("connection_id")
    filt_spec = body.get("filter")
    if not filt_spec:
        raise web.HTTPBadRequest(reason="Missing filter")
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
    conn_record = None
    try:
        async with context.session() as session:
            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        (cred_ex_record, cred_offer_message,) = await _create_free_offer(
            context.profile,
            filt_spec,
            conn_id,
            auto_issue,
            auto_remove,
            preview_spec,
            comment,
            trace_msg,
        )
        result = cred_ex_record.serialize()

    except (
        StorageNotFoundError,
        BaseModelError,
        V20CredManagerError,
        LedgerError,
    ) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_offer_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_offer_message,
        outcome="credential_exchange_send_free_offer.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send holder a credential offer in reference to a proposal with preview",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    cred_ex_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    conn_record = None
    try:
        async with context.session() as session:
            try:
                cred_ex_record = await V20CredExRecord.retrieve_by_id(
                    session,
                    cred_ex_id,
                )
            except StorageNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err

            conn_id = cred_ex_record.conn_id
            if cred_ex_record.state != (
                V20CredExRecord.STATE_PROPOSAL_RECEIVED
            ):  # check state here: manager call creates free offers too
                raise V20CredManagerError(
                    f"Credential exchange record {cred_ex_record.cred_exchange_id} "
                    f"in {cred_ex_record.state} state "
                    f"(must be {V20CredExRecord.STATE_PROPOSAL_RECEIVED})"
                )

            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_offer_message) = await cred_manager.create_offer(
            cred_ex_record,
            comment=None,
        )

        result = cred_ex_record.serialize()

    except (StorageError, BaseModelError, V20CredManagerError, LedgerError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_offer_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_offer_message,
        outcome="credential_exchange_send_bound_offer.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send issuer a credential request",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@response_schema(V20CredExRecordSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    cred_ex_id = request.match_info["cred_ex_id"]

    cred_ex_record = None
    conn_record = None
    try:
        async with context.session() as session:
            try:
                cred_ex_record = await V20CredExRecord.retrieve_by_id(
                    session,
                    cred_ex_id,
                )
            except StorageNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err
            conn_id = cred_ex_record.conn_id

            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_request_message) = await cred_manager.create_request(
            cred_ex_record,
            conn_record.my_did,
        )

        result = cred_ex_record.serialize()

    except (StorageError, V20CredManagerError, BaseModelError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_request_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_request_message,
        outcome="credential_exchange_send_request.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Send holder a credential",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@request_schema(V20CredIssueRequestSchema())
@response_schema(V20CredExRecordDetailSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    body = await request.json()
    comment = body.get("comment")

    cred_ex_id = request.match_info["cred_ex_id"]

    cred_ex_record = None
    conn_record = None
    try:
        async with context.session() as session:
            try:
                cred_ex_record = await V20CredExRecord.retrieve_by_id(
                    session,
                    cred_ex_id,
                )
            except StorageNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err
            conn_id = cred_ex_record.conn_id

            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_issue_message) = await cred_manager.issue_credential(
            cred_ex_record,
            comment=comment,
        )
        indy_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.INDY
        )
        dif_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.DIF
        )
        result = {
            "cred_ex_record": cred_ex_record.serialize(),
            "indy": indy_record.serialize() if indy_record else None,
            "dif": dif_record.serialize() if dif_record else None,
        }

    except (BaseModelError, V20CredManagerError, IndyIssuerError, StorageError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_issue_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_issue_message,
        outcome="credential_exchange_issue.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Store a received credential",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@request_schema(V20CredStoreRequestSchema())
@response_schema(V20CredExRecordDetailSchema(), 200, description="")
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
    outbound_handler = request["outbound_message_router"]

    try:
        body = await request.json() or {}
        cred_id = body.get("credential_id")
    except JSONDecodeError:
        cred_id = None

    cred_ex_id = request.match_info["cred_ex_id"]
    cred_ex_record = None
    conn_record = None
    try:
        async with context.session() as session:
            try:
                cred_ex_record = await V20CredExRecord.retrieve_by_id(
                    session,
                    cred_ex_id,
                )
            except StorageNotFoundError as err:
                raise web.HTTPNotFound(reason=err.roll_up) from err

            conn_id = cred_ex_record.conn_id
            conn_record = await ConnRecord.retrieve_by_id(session, conn_id)
            if not conn_record.is_ready:
                raise web.HTTPForbidden(reason=f"Connection {conn_id} not ready")

        cred_manager = V20CredManager(context.profile)
        (cred_ex_record, cred_stored_message) = await cred_manager.store_credential(
            cred_ex_record,
            cred_id,
        )
        indy_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.INDY
        )
        dif_record = await cred_manager.get_detail_record(
            cred_ex_id, V20CredFormat.Format.DIF
        )
        result = {
            "cred_ex_record": cred_ex_record.serialize(),
            "indy": indy_record.serialize() if indy_record else None,
            "dif": dif_record.serialize() if dif_record else None,
        }

    except (StorageError, V20CredManagerError, BaseModelError) as err:
        await internal_error(
            err,
            web.HTTPBadRequest,
            cred_ex_record or conn_record,
            outbound_handler,
        )

    await outbound_handler(cred_stored_message, connection_id=conn_id)

    trace_event(
        context.settings,
        cred_stored_message,
        outcome="credential_exchange_store.END",
        perf_counter=r_time,
    )

    return web.json_response(result)


@docs(
    tags=["issue-credential v2.0"],
    summary="Remove an existing credential exchange record",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@response_schema(V20IssueCredentialModuleResponseSchema(), 200, description="")
async def credential_exchange_remove(request: web.BaseRequest):
    """
    Request handler for removing a credential exchange record.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    cred_ex_id = request.match_info["cred_ex_id"]
    try:
        cred_manager = V20CredManager(context.profile)
        await cred_manager.delete_cred_ex_record(cred_ex_id)
    except StorageNotFoundError as err:
        await internal_error(err, web.HTTPNotFound, None, outbound_handler)
    except StorageError as err:
        await internal_error(err, web.HTTPBadRequest, None, outbound_handler)

    return web.json_response({})


@docs(
    tags=["issue-credential v2.0"],
    summary="Send a problem report for credential exchange",
)
@match_info_schema(V20CredExIdMatchInfoSchema())
@request_schema(V20CredIssueProblemReportRequestSchema())
@response_schema(V20IssueCredentialModuleResponseSchema(), 200, description="")
async def credential_exchange_problem_report(request: web.BaseRequest):
    """
    Request handler for sending problem report.

    Args:
        request: aiohttp request object

    """
    r_time = get_timer()

    context: AdminRequestContext = request["context"]
    outbound_handler = request["outbound_message_router"]

    cred_ex_id = request.match_info["cred_ex_id"]
    body = await request.json()

    try:
        async with await context.session() as session:
            cred_ex_record = await V20CredExRecord.retrieve_by_id(
                session,
                cred_ex_id,
            )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    error_result = ProblemReport(explain_ltxt=body["explain_ltxt"])
    error_result.assign_thread_id(cred_ex_record.thread_id)

    await outbound_handler(error_result, connection_id=cred_ex_record.conn_id)

    trace_event(
        context.settings,
        error_result,
        outcome="credential_exchange_problem_report.END",
        perf_counter=r_time,
    )

    return web.json_response({})


async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get(
                "/issue-credential-2.0/records",
                credential_exchange_list,
                allow_head=False,
            ),
            web.get(
                "/issue-credential-2.0/records/{cred_ex_id}",
                credential_exchange_retrieve,
                allow_head=False,
            ),
            web.post("/issue-credential-2.0/create", credential_exchange_create),
            web.post("/issue-credential-2.0/send", credential_exchange_send),
            web.post(
                "/issue-credential-2.0/send-proposal", credential_exchange_send_proposal
            ),
            web.post(
                "/issue-credential-2.0/send-offer", credential_exchange_send_free_offer
            ),
            web.post(
                "/issue-credential-2.0/records/{cred_ex_id}/send-offer",
                credential_exchange_send_bound_offer,
            ),
            web.post(
                "/issue-credential-2.0/records/{cred_ex_id}/send-request",
                credential_exchange_send_request,
            ),
            web.post(
                "/issue-credential-2.0/records/{cred_ex_id}/issue",
                credential_exchange_issue,
            ),
            web.post(
                "/issue-credential-2.0/records/{cred_ex_id}/store",
                credential_exchange_store,
            ),
            web.post(
                "/issue-credential-2.0/records/{cred_ex_id}/problem-report",
                credential_exchange_problem_report,
            ),
            web.delete(
                "/issue-credential-2.0/records/{cred_ex_id}",
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
            "name": "issue-credential v2.0",
            "description": "Credential issue v2.0",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
