"""Revocation registry admin routes."""

import json
import logging
import os
import shutil
from asyncio import shield
import re
import uuid

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
from ..anoncreds.base import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
)
from ..anoncreds.issuer import AnonCredsIssuerError
from ..anoncreds.registry import AnonCredsRegistry
from ..anoncreds.revocation import AnonCredsRevocation, AnonCredsRevocationError
from ..askar.profile import AskarProfile
from ..indy.models.revocation import IndyRevRegDef

from ..admin.request_context import AdminRequestContext
from ..connections.models.conn_record import ConnRecord
from ..core.event_bus import Event, EventBus
from ..core.profile import Profile
from ..indy.issuer import IndyIssuerError
from ..ledger.base import BaseLedger
from ..ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ..ledger.error import LedgerError
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.responder import BaseResponder
from ..messaging.valid import (
    INDY_CRED_DEF_ID,
    INDY_CRED_REV_ID,
    INDY_REV_REG_ID,
    INDY_REV_REG_SIZE,
    UUID4,
    WHOLE_NUM,
    UUIDFour,
)
from ..protocols.endorse_transaction.v1_0.manager import (
    TransactionManager,
    TransactionManagerError,
)
from ..protocols.endorse_transaction.v1_0.models.transaction_record import (
    TransactionRecordSchema,
)
from ..storage.error import StorageError, StorageNotFoundError

from .error import RevocationError
from .indy import IndyRevocation
from .manager import RevocationManager, RevocationManagerError
from .models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
    IssuerCredRevRecordSchema,
)
from .models.issuer_rev_reg_record import IssuerRevRegRecord, IssuerRevRegRecordSchema
from .util import (
    REVOCATION_EVENT_PREFIX,
    REVOCATION_REG_INIT_EVENT,
    REVOCATION_REG_ENDORSED_EVENT,
    REVOCATION_ENTRY_EVENT,
    notify_revocation_entry_event,
)


LOGGER = logging.getLogger(__name__)


class RevocationModuleResponseSchema(OpenAPISchema):
    """Response schema for Revocation Module."""


class RevRegCreateRequestSchema(OpenAPISchema):
    """Request schema for revocation registry creation request."""

    credential_definition_id = fields.Str(
        description="Credential definition identifier", **INDY_CRED_DEF_ID
    )
    max_cred_num = fields.Int(
        required=False,
        description="Revocation registry size",
        strict=True,
        **INDY_REV_REG_SIZE,
    )


class RevRegResultSchema(OpenAPISchema):
    """Result schema for revocation registry creation request."""

    result = fields.Nested(IssuerRevRegRecordSchema())


class TxnOrRevRegResultSchema(OpenAPISchema):
    """Result schema for credential definition send request."""

    sent = fields.Nested(
        RevRegResultSchema(),
        required=False,
        definition="Content sent",
    )
    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="Revocation registry definition transaction to endorse",
    )


class CredRevRecordQueryStringSchema(OpenAPISchema):
    """Parameters and validators for credential revocation record request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields - must have (rr-id and cr-id) xor cx-id."""

        rev_reg_id = data.get("rev_reg_id")
        cred_rev_id = data.get("cred_rev_id")
        cred_ex_id = data.get("cred_ex_id")

        if not (
            (rev_reg_id and cred_rev_id and not cred_ex_id)
            or (cred_ex_id and not rev_reg_id and not cred_rev_id)
        ):
            raise ValidationError(
                "Request must have either rev_reg_id and cred_rev_id or cred_ex_id"
            )

    rev_reg_id = fields.Str(
        description="Revocation registry identifier",
        required=False,
        **INDY_REV_REG_ID,
    )
    cred_rev_id = fields.Str(
        description="Credential revocation identifier",
        required=False,
        **INDY_CRED_REV_ID,
    )
    cred_ex_id = fields.Str(
        description="Credential exchange identifier",
        required=False,
        **UUID4,
    )


class RevRegId(OpenAPISchema):
    """Parameters and validators for delete tails file request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate schema fields - must have either rr-id or cr-id."""

        rev_reg_id = data.get("rev_reg_id")
        cred_def_id = data.get("cred_def_id")

        if not (rev_reg_id or cred_def_id):
            raise ValidationError("Request must have either rev_reg_id or cred_def_id")

    rev_reg_id = fields.Str(
        description="Revocation registry identifier",
        required=False,
        **INDY_REV_REG_ID,
    )
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )


class RevokeRequestSchema(CredRevRecordQueryStringSchema):
    """Parameters and validators for revocation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate fields - connection_id and thread_id must be present if notify."""
        super().validate_fields(data, **kwargs)

        notify = data.get("notify")
        connection_id = data.get("connection_id")
        notify_version = data.get("notify_version", "v1_0")

        if notify and not connection_id:
            raise ValidationError(
                "Request must specify connection_id if notify is true"
            )
        if notify and not notify_version:
            raise ValidationError(
                "Request must specify notify_version if notify is true"
            )

    publish = fields.Boolean(
        description=(
            "(True) publish revocation to ledger immediately, or "
            "(default, False) mark it pending"
        ),
        required=False,
    )
    notify = fields.Boolean(
        description="Send a notification to the credential recipient",
        required=False,
    )
    notify_version = fields.String(
        description="Specify which version of the revocation notification should be sent",
        validate=validate.OneOf(["v1_0", "v2_0"]),
        required=False,
    )
    connection_id = fields.Str(
        description=(
            "Connection ID to which the revocation notification will be sent; "
            "required if notify is true"
        ),
        required=False,
        **UUID4,
    )
    thread_id = fields.Str(
        description=(
            "Thread ID of the credential exchange message thread resulting in "
            "the credential now being revoked; required if notify is true"
        ),
        required=False,
    )
    comment = fields.Str(
        description="Optional comment to include in revocation notification",
        required=False,
    )


class PublishRevocationsSchema(OpenAPISchema):
    """Request and result schema for revocation publication API call."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(example=INDY_REV_REG_ID["example"]),  # marshmallow 3.0 ignores
        values=fields.List(
            fields.Str(
                description="Credential revocation identifier", **INDY_CRED_REV_ID
            )
        ),
        description="Credential revocation ids by revocation registry id",
    )


class TxnOrPublishRevocationsResultSchema(OpenAPISchema):
    """Result schema for credential definition send request."""

    sent = fields.Nested(
        PublishRevocationsSchema(),
        required=False,
        definition="Content sent",
    )
    txn = fields.Nested(
        TransactionRecordSchema(),
        required=False,
        description="Revocation registry revocations transaction to endorse",
    )


class ClearPendingRevocationsRequestSchema(OpenAPISchema):
    """Request schema for clear pending revocations API call."""

    purge = fields.Dict(
        required=False,
        keys=fields.Str(example=INDY_REV_REG_ID["example"]),  # marshmallow 3.0 ignores
        values=fields.List(
            fields.Str(
                description="Credential revocation identifier", **INDY_CRED_REV_ID
            )
        ),
        description=(
            "Credential revocation ids by revocation registry id: omit for all, "
            "specify null or empty list for all pending per revocation registry"
        ),
    )


class CredRevRecordResultSchema(OpenAPISchema):
    """Result schema for credential revocation record request."""

    result = fields.Nested(IssuerCredRevRecordSchema())


class CredRevRecordDetailsResultSchema(OpenAPISchema):
    """Result schema for credential revocation record request."""

    results = fields.List(fields.Nested(IssuerCredRevRecordSchema()))


class CredRevIndyRecordsResultSchema(OpenAPISchema):
    """Result schema for revoc reg delta."""

    rev_reg_delta = fields.Dict(
        description="Indy revocation registry delta",
    )


class RevRegIssuedResultSchema(OpenAPISchema):
    """Result schema for revocation registry credentials issued request."""

    result = fields.Int(
        description="Number of credentials issued against revocation registry",
        strict=True,
        **WHOLE_NUM,
    )


class RevRegUpdateRequestMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    apply_ledger_update = fields.Bool(
        description="Apply updated accumulator transaction to ledger",
        required=True,
    )


class RevRegWalletUpdatedResultSchema(OpenAPISchema):
    """Number of wallet revocation entries status updated."""

    rev_reg_delta = fields.Dict(
        description="Indy revocation registry delta",
    )
    accum_calculated = fields.Dict(
        description="Calculated accumulator for phantom revocations",
    )
    accum_fixed = fields.Dict(
        description="Applied ledger transaction to fix revocations",
    )


class RevRegsCreatedSchema(OpenAPISchema):
    """Result schema for request for revocation registries created."""

    rev_reg_ids = fields.List(
        fields.Str(description="Revocation registry identifiers", **INDY_REV_REG_ID)
    )


class RevRegUpdateTailsFileUriSchema(OpenAPISchema):
    """Request schema for updating tails file URI."""

    tails_public_uri = fields.Url(
        description="Public URI to the tails file",
        example=(
            "http://192.168.56.133:6543/revocation/registry/"
            f"{INDY_REV_REG_ID['example']}/tails-file"
        ),
        required=True,
    )


class RevRegsCreatedQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for rev regs created request."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=False,
        **INDY_CRED_DEF_ID,
    )
    state = fields.Str(
        description="Revocation registry state",
        required=False,
        validate=validate.OneOf(
            [
                getattr(IssuerRevRegRecord, m)
                for m in vars(IssuerRevRegRecord)
                if m.startswith("STATE_")
            ]
        ),
    )


class SetRevRegStateQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for request to set rev reg state."""

    state = fields.Str(
        description="Revocation registry state to set",
        required=True,
        validate=validate.OneOf(
            [
                getattr(IssuerRevRegRecord, m)
                for m in vars(IssuerRevRegRecord)
                if m.startswith("STATE_")
            ]
        ),
    )


class RevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        description="Revocation Registry identifier",
        required=True,
        **INDY_REV_REG_ID,
    )


class RevocationCredDefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )


class CreateRevRegTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        description="Create Transaction For Endorser's signature",
        required=False,
    )


class RevRegConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        description="Connection identifier", required=False, example=UUIDFour.EXAMPLE
    )


@docs(
    tags=["revocation"],
    summary="Revoke an issued credential",
)
@request_schema(RevokeRequestSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def revoke(request: web.BaseRequest):
    """
    Request handler for storing a credential revocation.

    Args:
        request: aiohttp request object

    Returns:
        The credential revocation details.

    """
    #
    # this is exactly what is in anoncreds /revocation/revoke.
    # we cannot import the revoke function as it imports classes from here,
    # so circular dependency.
    # we will clean this up and DRY at some point.
    #
    context: AdminRequestContext = request["context"]
    body = await request.json()
    cred_ex_id = body.get("cred_ex_id")
    body["notify"] = body.get("notify", context.settings.get("revocation.notify"))
    notify = body.get("notify")
    connection_id = body.get("connection_id")
    body["notify_version"] = body.get("notify_version", "v1_0")
    notify_version = body["notify_version"]

    if notify and not connection_id:
        raise web.HTTPBadRequest(reason="connection_id must be set when notify is true")
    if notify and not notify_version:
        raise web.HTTPBadRequest(
            reason="Request must specify notify_version if notify is true"
        )

    rev_manager = RevocationManager(context.profile)
    try:
        if cred_ex_id:
            # rev_reg_id and cred_rev_id should not be present so we can
            # safely splat the body
            await rev_manager.revoke_credential_by_cred_ex_id(**body)
        else:
            # no cred_ex_id so we can safely splat the body
            await rev_manager.revoke_credential(**body)
    except (
        RevocationManagerError,
        AnonCredsRevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRegistrationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({})


@docs(tags=["revocation"], summary="Publish pending revocations to ledger")
@request_schema(PublishRevocationsSchema())
@response_schema(TxnOrPublishRevocationsResultSchema(), 200, description="")
async def publish_revocations(request: web.BaseRequest):
    """
    Request handler for publishing pending revocations to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        Credential revocation ids published as revoked by revocation registry id.

    """
    #
    # this is exactly what is in anoncreds /revocation/publish-revocations.
    # we cannot import the function as it imports classes from here,
    # so circular dependency.
    # we will clean this up and DRY at some point.
    #
    context: AdminRequestContext = request["context"]
    body = await request.json()
    rrid2crid = body.get("rrid2crid")

    rev_manager = RevocationManager(context.profile)

    try:
        rev_reg_resp = await rev_manager.publish_pending_revocations(
            rrid2crid,
        )
    except (
        RevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRevocationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    return web.json_response({"rrid2crid": rev_reg_resp})


@docs(
    tags=["revocation"],
    summary="Search for matching revocation registries that current agent created",
)
@querystring_schema(RevRegsCreatedQueryStringSchema())
@response_schema(RevRegsCreatedSchema(), 200, description="")
async def rev_regs_created(request: web.BaseRequest):
    """
    Request handler to get revocation registries that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        List of identifiers of matching revocation registries.

    """
    context: AdminRequestContext = request["context"]

    search_tags = [
        tag for tag in vars(RevRegsCreatedQueryStringSchema)["_declared_fields"]
    ]
    tag_filter = {
        tag: request.query[tag] for tag in search_tags if tag in request.query
    }
    async with context.profile.session() as session:
        found = await IssuerRevRegRecord.query(
            session,
            tag_filter,
            post_filter_negative={"state": IssuerRevRegRecord.STATE_INIT},
        )

    return web.json_response(
        {
            "rev_reg_ids": [
                record.revoc_reg_id for record in found if record.revoc_reg_id
            ]
        }
    )


@docs(
    tags=["revocation"],
    summary="Get revocation registry by revocation registry id",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegResultSchema(), 200, description="")
async def get_rev_reg(request: web.BaseRequest):
    """
    Request handler to get a revocation registry by rev reg id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry

    """
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    rev_reg_id = request.match_info["rev_reg_id"]
    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)

    return web.json_response({"result": rev_reg.serialize()})


async def _get_issuer_rev_reg_record(
    profile: AskarProfile, rev_reg_id
) -> IssuerRevRegRecord:
    # fetch rev reg def from anoncreds
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")
        # looking good, so grab some other data
        state = await revocation.get_created_revocation_registry_definition_state(
            rev_reg_id
        )
        pending_pubs = await revocation.get_pending_revocations(rev_reg_id)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    # transform
    result = IssuerRevRegRecord(
        record_id=uuid.uuid4(),
        state=state,
        cred_def_id=rev_reg_def.cred_def_id,
        error_msg=None,
        issuer_did=rev_reg_def.issuer_id,
        max_cred_num=rev_reg_def.value.max_cred_num,
        revoc_def_type="CL_ACCUM",
        revoc_reg_id=rev_reg_id,
        revoc_reg_def=IndyRevRegDef(
            ver="1.0",
            id_=rev_reg_id,
            revoc_def_type="CL_ACCUM",
            tag=rev_reg_def.tag,
            cred_def_id=rev_reg_def.cred_def_id,
            value=None,
        ),
        revoc_reg_entry=None,
        tag=rev_reg_def.tag,
        tails_hash=rev_reg_def.value.tails_hash,
        tails_local_path=rev_reg_def.value.tails_location,
        tails_public_uri=None,
        pending_pub=pending_pubs,
    )
    return result


@docs(
    tags=["revocation"],
    summary="Get number of credentials issued against revocation registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegIssuedResultSchema(), 200, description="")
async def get_rev_reg_issued_count(request: web.BaseRequest):
    """
    Request handler to get number of credentials issued against revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials issued against revocation registry

    """
    context: AdminRequestContext = request["context"]

    rev_reg_id = request.match_info["rev_reg_id"]

    async with context.profile.session() as session:
        try:
            await IssuerRevRegRecord.retrieve_by_revoc_reg_id(session, rev_reg_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        count = len(
            await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
        )

    return web.json_response({"result": count})


@docs(
    tags=["revocation"],
    summary="Get details of credentials issued against revocation registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(CredRevRecordDetailsResultSchema(), 200, description="")
async def get_rev_reg_issued(request: web.BaseRequest):
    """
    Request handler to get credentials issued against revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials issued against revocation registry

    """
    context: AdminRequestContext = request["context"]

    rev_reg_id = request.match_info["rev_reg_id"]

    recs = []
    async with context.profile.session() as session:
        try:
            await IssuerRevRegRecord.retrieve_by_revoc_reg_id(session, rev_reg_id)
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err
        recs = await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
    results = []
    for rec in recs:
        results.append(rec.serialize())

    return web.json_response(results)


@docs(
    tags=["revocation"],
    summary="Get details of revoked credentials from ledger",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(CredRevIndyRecordsResultSchema(), 200, description="")
async def get_rev_reg_indy_recs(request: web.BaseRequest):
    """
    Request handler to get details of revoked credentials from ledger.

    Args:
        request: aiohttp request object

    Returns:
        Details of revoked credentials from ledger

    """
    context: AdminRequestContext = request["context"]
    rev_reg_id = request.match_info["rev_reg_id"]
    profile: AskarProfile = context.profile
    try:
        revocation = AnonCredsRegistry(profile)
        rev_reg_delta = await revocation.get_revocation_registry_delta(
            profile, rev_reg_id
        )
    except (AnonCredsObjectNotFound, AnonCredsResolutionError) as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response(
        {
            "rev_reg_delta": rev_reg_delta,
        }
    )


@docs(
    tags=["revocation"],
    summary="Fix revocation state in wallet and return number of updated entries",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@querystring_schema(RevRegUpdateRequestMatchInfoSchema())
@response_schema(RevRegWalletUpdatedResultSchema(), 200, description="")
async def update_rev_reg_revoked_state(request: web.BaseRequest):
    """
    Request handler to fix ledger entry of credentials revoked against registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials posted to ledger

    """
    context: AdminRequestContext = request["context"]

    rev_reg_id = request.match_info["rev_reg_id"]

    apply_ledger_update_json = request.query.get("apply_ledger_update", "false")
    LOGGER.debug(">>> apply_ledger_update_json = %s", apply_ledger_update_json)
    apply_ledger_update = json.loads(request.query.get("apply_ledger_update", "false"))

    rev_reg_record = None
    genesis_transactions = None
    async with context.profile.session() as session:
        try:
            rev_reg_record = await IssuerRevRegRecord.retrieve_by_revoc_reg_id(
                session, rev_reg_id
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        if not genesis_transactions:
            ledger_manager = context.injector.inject(BaseMultipleLedgerManager)
            write_ledgers = await ledger_manager.get_write_ledger()
            LOGGER.debug(f"write_ledgers = {write_ledgers}")
            pool = write_ledgers[1].pool
            LOGGER.debug(f"write_ledger pool = {pool}")

            genesis_transactions = pool.genesis_txns

        if not genesis_transactions:
            raise web.HTTPInternalServerError(
                reason="no genesis_transactions for writable ledger"
            )

        if apply_ledger_update:
            ledger = session.inject_or(BaseLedger)
            if not ledger:
                reason = "No ledger available"
                if not session.context.settings.get_value("wallet.type"):
                    reason += ": missing wallet-type?"
                raise web.HTTPInternalServerError(reason=reason)

    rev_manager = RevocationManager(context.profile)
    try:
        (
            rev_reg_delta,
            recovery_txn,
            applied_txn,
        ) = await rev_manager.update_rev_reg_revoked_state(
            apply_ledger_update, rev_reg_record, genesis_transactions
        )
    except (
        RevocationManagerError,
        RevocationError,
        StorageError,
        IndyIssuerError,
        LedgerError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up)
    except Exception as err:
        raise web.HTTPBadRequest(reason=str(err))

    return web.json_response(
        {
            "rev_reg_delta": rev_reg_delta,
            "accum_calculated": recovery_txn,
            "accum_fixed": applied_txn,
        }
    )


@docs(
    tags=["revocation"],
    summary="Get credential revocation status",
)
@querystring_schema(CredRevRecordQueryStringSchema())
@response_schema(CredRevRecordResultSchema(), 200, description="")
async def get_cred_rev_record(request: web.BaseRequest):
    """
    Request handler to get credential revocation record.

    Args:
        request: aiohttp request object

    Returns:
        The issuer credential revocation record

    """
    context: AdminRequestContext = request["context"]

    rev_reg_id = request.query.get("rev_reg_id")
    cred_rev_id = request.query.get("cred_rev_id")  # numeric string
    cred_ex_id = request.query.get("cred_ex_id")

    try:
        async with context.profile.session() as session:
            if rev_reg_id and cred_rev_id:
                rec = await IssuerCredRevRecord.retrieve_by_ids(
                    session, rev_reg_id, cred_rev_id
                )
            else:
                rec = await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                    session, cred_ex_id
                )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({"result": rec.serialize()})


@docs(
    tags=["revocation"],
    summary="Download tails file",
    produces=["application/octet-stream"],
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema, description="tails file")
async def get_tails_file(request: web.BaseRequest) -> web.FileResponse:
    """
    Request handler to download tails file for revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The tails file in FileResponse

    """
    #
    # there is no equivalent of this in anoncreds.
    # do we need it there or is this only for tranisition.
    #
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    tails_local_path = rev_reg_def.value.tails_location
    return web.FileResponse(path=tails_local_path, status=200)


@docs(
    tags=["revocation"],
    summary="Upload local tails file to server",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationModuleResponseSchema(), description="")
async def upload_tails_file(request: web.BaseRequest):
    """
    Request handler to upload local tails file for revocation registry.

    Args:
        request: aiohttp request object

    """
    #
    # this is exactly what is in anoncreds /revocation/upload-tails-file.
    # we cannot import the function as it imports classes from here,
    # so circular dependency.
    # we will clean this up and DRY at some point.
    #
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")

        await revocation.upload_tails_file(rev_reg_def)

    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({})


@docs(
    tags=["revocation"],
    summary="Update revocation registry with new public URI to its tails file",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@request_schema(RevRegUpdateTailsFileUriSchema())
@response_schema(RevRegResultSchema(), 200, description="")
async def update_rev_reg(request: web.BaseRequest):
    """
    Request handler to update a rev reg's public tails URI by registry id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record

    """
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    rev_reg_id = request.match_info["rev_reg_id"]
    body = await request.json()
    tails_public_uri = body.get("tails_public_uri")
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.set_tails_file_public_uri(
            rev_reg_id, tails_public_uri
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")

    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)
    return web.json_response({"result": rev_reg.serialize()})


@docs(tags=["revocation"], summary="Set revocation registry state manually")
@match_info_schema(RevRegIdMatchInfoSchema())
@querystring_schema(SetRevRegStateQueryStringSchema())
@response_schema(RevRegResultSchema(), 200, description="")
async def set_rev_reg_state(request: web.BaseRequest):
    """
    Request handler to set a revocation registry state manually.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record, updated

    """
    context: AdminRequestContext = request["context"]
    profile: AskarProfile = context.profile
    rev_reg_id = request.match_info["rev_reg_id"]
    state = request.query.get("state")

    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.set_rev_reg_state(rev_reg_id, state)
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")

    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)
    return web.json_response({"result": rev_reg.serialize()})


def register_events(event_bus: EventBus):
    """Subscribe to any events we need to support."""
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_REG_INIT_EVENT}.*"),
        on_revocation_registry_init_event,
    )
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_REG_ENDORSED_EVENT}.*"),
        on_revocation_registry_endorsed_event,
    )
    event_bus.subscribe(
        re.compile(f"^{REVOCATION_EVENT_PREFIX}{REVOCATION_ENTRY_EVENT}.*"),
        on_revocation_entry_event,
    )


async def on_revocation_registry_init_event(profile: Profile, event: Event):
    """Handle revocation registry initiation event."""
    meta_data = event.payload
    if "endorser" in meta_data:
        # TODO error handling - for now just let exceptions get raised
        endorser_connection_id = meta_data["endorser"]["connection_id"]
        async with profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(
                session, endorser_connection_id
            )
            endorser_info = await connection.metadata_get(session, "endorser_info")
        endorser_did = endorser_info["endorser_did"]
        write_ledger = False
    else:
        endorser_connection_id = None
        endorser_did = None
        write_ledger = True

    tails_base_url = profile.settings.get("tails_server_base_url")
    if not tails_base_url:
        raise RevocationError("tails_server_base_url not configured")

    # Generate the registry and upload the tails file
    async def generate(rr_record: IssuerRevRegRecord) -> dict:
        await rr_record.generate_registry(profile)
        public_uri = tails_base_url.rstrip("/") + f"/{registry_record.revoc_reg_id}"
        await rr_record.set_tails_file_public_uri(profile, public_uri)
        rev_reg_resp = await rr_record.send_def(
            profile,
            write_ledger=write_ledger,
            endorser_did=endorser_did,
        )
        if write_ledger:
            # Upload the tails file
            await rr_record.upload_tails_file(profile)

            # Post the initial revocation entry
            await notify_revocation_entry_event(profile, record_id, meta_data)
        else:
            transaction_manager = TransactionManager(profile)
            try:
                revo_transaction = await transaction_manager.create_record(
                    messages_attach=rev_reg_resp["result"],
                    connection_id=connection.connection_id,
                    meta_data=event.payload,
                )
            except StorageError as err:
                raise TransactionManagerError(reason=err.roll_up) from err

            # if auto-request, send the request to the endorser
            if profile.settings.get_value("endorser.auto_request"):
                try:
                    (
                        revo_transaction,
                        revo_transaction_request,
                    ) = await transaction_manager.create_request(
                        transaction=revo_transaction,
                        # TODO see if we need to parameterize these params
                        # expires_time=expires_time,
                        # endorser_write_txn=endorser_write_txn,
                    )
                except (StorageError, TransactionManagerError) as err:
                    raise TransactionManagerError(reason=err.roll_up) from err

                responder = profile.inject_or(BaseResponder)
                if responder:
                    await responder.send(
                        revo_transaction_request,
                        connection_id=connection.connection_id,
                    )
                else:
                    LOGGER.warning(
                        "Configuration has no BaseResponder: cannot update "
                        "revocation on registry ID: %s",
                        record_id,
                    )

    record_id = meta_data["context"]["issuer_rev_id"]
    async with profile.session() as session:
        registry_record = await IssuerRevRegRecord.retrieve_by_id(session, record_id)
    await shield(generate(registry_record))

    create_pending_rev_reg = meta_data["processing"].get(
        "create_pending_rev_reg", False
    )
    if write_ledger and create_pending_rev_reg:
        revoc = IndyRevocation(profile)
        await revoc.init_issuer_registry(
            registry_record.cred_def_id,
            registry_record.max_cred_num,
            registry_record.revoc_def_type,
            endorser_connection_id=endorser_connection_id,
        )


async def on_revocation_entry_event(profile: Profile, event: Event):
    """Handle revocation entry event."""
    meta_data = event.payload
    if "endorser" in meta_data:
        # TODO error handling - for now just let exceptions get raised
        async with profile.session() as session:
            connection = await ConnRecord.retrieve_by_id(
                session, meta_data["endorser"]["connection_id"]
            )
            endorser_info = await connection.metadata_get(session, "endorser_info")
        endorser_did = endorser_info["endorser_did"]
        write_ledger = False
    else:
        endorser_did = None
        write_ledger = True

    record_id = meta_data["context"]["issuer_rev_id"]
    async with profile.session() as session:
        registry_record = await IssuerRevRegRecord.retrieve_by_id(session, record_id)
    rev_entry_resp = await registry_record.send_entry(
        profile,
        write_ledger=write_ledger,
        endorser_did=endorser_did,
    )

    if not write_ledger:
        transaction_manager = TransactionManager(profile)
        try:
            revo_transaction = await transaction_manager.create_record(
                messages_attach=rev_entry_resp["result"],
                connection_id=connection.connection_id,
                meta_data=meta_data,
            )
        except StorageError as err:
            raise RevocationError(err.roll_up) from err

        # if auto-request, send the request to the endorser
        if profile.settings.get_value("endorser.auto_request"):
            try:
                (
                    revo_transaction,
                    revo_transaction_request,
                ) = await transaction_manager.create_request(
                    transaction=revo_transaction,
                    # TODO see if we need to parameterize these params
                    # expires_time=expires_time,
                    # endorser_write_txn=endorser_write_txn,
                )
            except (StorageError, TransactionManagerError) as err:
                raise RevocationError(err.roll_up) from err

            responder = profile.inject_or(BaseResponder)
            if responder:
                await responder.send(
                    revo_transaction_request,
                    connection_id=connection.connection_id,
                )
            else:
                LOGGER.warning(
                    "Configuration has no BaseResponder: cannot update "
                    "revocation on cred def %s",
                    meta_data["endorser"]["cred_def_id"],
                )


async def on_revocation_registry_endorsed_event(profile: Profile, event: Event):
    """Handle revocation registry endorsement event."""
    meta_data = event.payload
    rev_reg_id = meta_data["context"]["rev_reg_id"]
    revoc = IndyRevocation(profile)
    registry_record = await revoc.get_issuer_rev_reg_record(rev_reg_id)

    if profile.settings.get_value("endorser.auto_request"):
        # NOTE: if there are multiple pods, then the one processing this
        # event may not be the one that generated the tails file.
        await registry_record.upload_tails_file(profile)

        # Post the initial revocation entry
        await notify_revocation_entry_event(
            profile, registry_record.record_id, meta_data
        )

    # create a "pending" registry if one is requested
    # (this is done automatically when creating a credential definition, so that when a
    #   revocation registry fills up, we can continue to issue credentials without a
    #   delay)
    create_pending_rev_reg = meta_data["processing"].get(
        "create_pending_rev_reg", False
    )
    if create_pending_rev_reg:
        endorser_connection_id = (
            meta_data["endorser"].get("connection_id", None)
            if "endorser" in meta_data
            else None
        )
        await revoc.init_issuer_registry(
            registry_record.cred_def_id,
            registry_record.max_cred_num,
            registry_record.revoc_def_type,
            endorser_connection_id=endorser_connection_id,
        )


class TailsDeleteResponseSchema(OpenAPISchema):
    """Return schema for tails failes deletion."""

    message = fields.Str()


@querystring_schema(RevRegId())
@response_schema(TailsDeleteResponseSchema())
@docs(tags=["revocation"], summary="Delete the tail files")
async def delete_tails(request: web.BaseRequest) -> json:
    """Delete Tails Files."""
    context: AdminRequestContext = request["context"]
    rev_reg_id = request.query.get("rev_reg_id")
    cred_def_id = request.query.get("cred_def_id")
    revoc = IndyRevocation(context.profile)
    session = revoc._profile.session()
    if rev_reg_id:
        rev_reg = await revoc.get_issuer_rev_reg_record(rev_reg_id)
        tails_path = rev_reg.tails_local_path
        main_dir_rev = os.path.dirname(tails_path)
        try:
            shutil.rmtree(main_dir_rev)
            return web.json_response({"message": "All files deleted successfully"})
        except Exception as e:
            return web.json_response({"message": str(e)})
    elif cred_def_id:
        async with session:
            cred_reg = sorted(
                await IssuerRevRegRecord.query_by_cred_def_id(
                    session, cred_def_id, IssuerRevRegRecord.STATE_GENERATED
                )
            )[0]
        tails_path = cred_reg.tails_local_path
        main_dir_rev = os.path.dirname(tails_path)
        main_dir_cred = os.path.dirname(main_dir_rev)
        filenames = os.listdir(main_dir_cred)
        try:
            flag = 0
            for i in filenames:
                safe_cred_def_id = re.escape(cred_def_id)
                if re.search(safe_cred_def_id, i):
                    shutil.rmtree(main_dir_cred + "/" + i)
                    flag = 1
            if flag:
                return web.json_response({"message": "All files deleted successfully"})
            else:
                return web.json_response({"message": "No such file or directory"})

        except Exception as e:
            return web.json_response({"message": str(e)})


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/revocation/revoke", revoke),
            web.post("/revocation/publish-revocations", publish_revocations),
            web.get(
                "/revocation/credential-record", get_cred_rev_record, allow_head=False
            ),
            web.get(
                "/revocation/registries/created",
                rev_regs_created,
                allow_head=False,
            ),
            web.get("/revocation/registry/{rev_reg_id}", get_rev_reg, allow_head=False),
            web.get(
                "/revocation/registry/{rev_reg_id}/issued",
                get_rev_reg_issued_count,
                allow_head=False,
            ),
            web.get(
                "/revocation/registry/{rev_reg_id}/issued/details",
                get_rev_reg_issued,
                allow_head=False,
            ),
            web.get(
                "/revocation/registry/{rev_reg_id}/issued/indy_recs",
                get_rev_reg_indy_recs,
                allow_head=False,
            ),
            web.patch("/revocation/registry/{rev_reg_id}", update_rev_reg),
            web.put("/revocation/registry/{rev_reg_id}/tails-file", upload_tails_file),
            web.get(
                "/revocation/registry/{rev_reg_id}/tails-file",
                get_tails_file,
                allow_head=False,
            ),
            web.patch(
                "/revocation/registry/{rev_reg_id}/set-state",
                set_rev_reg_state,
            ),
            web.put(
                "/revocation/registry/{rev_reg_id}/fix-revocation-entry-state",
                update_rev_reg_revoked_state,
            ),
            web.delete("/revocation/registry/delete-tails-file", delete_tails),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "revocation",
            "description": "Revocation registry management",
            "externalDocs": {
                "description": "Overview",
                "url": (
                    "https://github.com/hyperledger/indy-hipe/tree/"
                    "master/text/0011-cred-revocation"
                ),
            },
        }
    )

    # aio_http-apispec polite API only works on schema for JSON objects, not files yet
    methods = app._state["swagger_dict"]["paths"].get(
        "/revocation/registry/{rev_reg_id}/tails-file"
    )
    if methods:
        methods["get"]["responses"]["200"]["schema"] = {
            "type": "string",
            "format": "binary",
        }
