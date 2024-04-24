"""Revocation registry admin routes."""

import json
import logging
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

from ..admin.request_context import AdminRequestContext
from ..anoncreds.base import (
    AnonCredsObjectNotFound,
    AnonCredsRegistrationError,
    AnonCredsResolutionError,
)
from ..anoncreds.default.legacy_indy.registry import LegacyIndyRegistry
from ..anoncreds.issuer import AnonCredsIssuerError
from ..anoncreds.models.anoncreds_revocation import RevRegDefState
from ..anoncreds.revocation import AnonCredsRevocation, AnonCredsRevocationError
from ..anoncreds.routes import (
    create_transaction_for_endorser_description,
    endorser_connection_id_description,
)
from ..askar.profile_anon import AskarAnoncredsProfile
from ..indy.issuer import IndyIssuerError
from ..indy.models.revocation import IndyRevRegDef
from ..ledger.base import BaseLedger
from ..ledger.error import LedgerError
from ..ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ..messaging.models.openapi import OpenAPISchema
from ..messaging.valid import (
    INDY_CRED_DEF_ID_EXAMPLE,
    INDY_CRED_DEF_ID_VALIDATE,
    INDY_CRED_REV_ID_EXAMPLE,
    INDY_CRED_REV_ID_VALIDATE,
    INDY_REV_REG_ID_EXAMPLE,
    INDY_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
    WHOLE_NUM_EXAMPLE,
    WHOLE_NUM_VALIDATE,
    UUIDFour,
)
from ..revocation.error import RevocationError
from ..revocation.models.issuer_rev_reg_record import (
    IssuerRevRegRecord,
    IssuerRevRegRecordSchema,
)
from ..storage.error import StorageError, StorageNotFoundError
from ..utils.profiles import is_not_anoncreds_profile_raise_web_exception
from .manager import RevocationManager, RevocationManagerError
from .models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
    IssuerCredRevRecordSchemaAnoncreds,
)

LOGGER = logging.getLogger(__name__)

TAG_TITLE = "anoncreds - revocation"


class RevocationAnoncredsModuleResponseSchema(OpenAPISchema):
    """Response schema for Revocation Module."""


class RevRegResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for revocation registry creation request."""

    result = fields.Nested(IssuerRevRegRecordSchema())


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
        required=False,
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        required=False,
        validate=INDY_CRED_REV_ID_VALIDATE,
        metadata={
            "description": "Credential revocation identifier",
            "example": INDY_CRED_REV_ID_EXAMPLE,
        },
    )
    cred_ex_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": "Credential exchange identifier",
            "example": UUID4_EXAMPLE,
        },
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
        required=False,
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )
    cred_def_id = fields.Str(
        required=False,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )


class CredRevRecordResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    result = fields.Nested(IssuerCredRevRecordSchemaAnoncreds())


class CredRevRecordDetailsResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    results = fields.List(fields.Nested(IssuerCredRevRecordSchemaAnoncreds()))


class CredRevIndyRecordsResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for revoc reg delta."""

    rev_reg_delta = fields.Dict(
        metadata={"description": "Indy revocation registry delta"}
    )


class RevRegIssuedResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for revocation registry credentials issued request."""

    result = fields.Int(
        validate=WHOLE_NUM_VALIDATE,
        metadata={
            "description": "Number of credentials issued against revocation registry",
            "strict": True,
            "example": WHOLE_NUM_EXAMPLE,
        },
    )


class RevRegUpdateRequestMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    apply_ledger_update = fields.Bool(
        required=True,
        metadata={"description": "Apply updated accumulator transaction to ledger"},
    )


class RevRegWalletUpdatedResultSchemaAnoncreds(OpenAPISchema):
    """Number of wallet revocation entries status updated."""

    rev_reg_delta = fields.Dict(
        metadata={"description": "Indy revocation registry delta"}
    )
    accum_calculated = fields.Dict(
        metadata={"description": "Calculated accumulator for phantom revocations"}
    )
    accum_fixed = fields.Dict(
        metadata={"description": "Applied ledger transaction to fix revocations"}
    )


class RevRegsCreatedSchemaAnoncreds(OpenAPISchema):
    """Result schema for request for revocation registries created."""

    rev_reg_ids = fields.List(
        fields.Str(
            validate=INDY_REV_REG_ID_VALIDATE,
            metadata={
                "description": "Revocation registry identifiers",
                "example": INDY_REV_REG_ID_EXAMPLE,
            },
        )
    )


class RevRegUpdateTailsFileUriSchema(OpenAPISchema):
    """Request schema for updating tails file URI."""

    tails_public_uri = fields.Url(
        required=True,
        metadata={
            "description": "Public URI to the tails file",
            "example": (
                "http://192.168.56.133:6543/revocation/registry/"
                f"{INDY_REV_REG_ID_EXAMPLE}/tails-file"
            ),
        },
    )


class RevRegsCreatedQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for rev regs created request."""

    cred_def_id = fields.Str(
        required=False,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )
    state = fields.Str(
        required=False,
        validate=validate.OneOf(
            [
                getattr(RevRegDefState, m)
                for m in vars(RevRegDefState)
                if m.startswith("STATE_")
            ]
        ),
        metadata={"description": "Revocation registry state"},
    )


class SetRevRegStateQueryStringSchema(OpenAPISchema):
    """Query string parameters and validators for request to set rev reg state."""

    state = fields.Str(
        required=True,
        validate=validate.OneOf(
            [
                getattr(RevRegDefState, m)
                for m in vars(RevRegDefState)
                if m.startswith("STATE_")
            ]
        ),
        metadata={"description": "Revocation registry state to set"},
    )


class RevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        required=True,
        validate=INDY_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": INDY_REV_REG_ID_EXAMPLE,
        },
    )


class RevocationCredDefIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking cred def id."""

    cred_def_id = fields.Str(
        required=True,
        validate=INDY_CRED_DEF_ID_VALIDATE,
        metadata={
            "description": "Credential definition identifier",
            "example": INDY_CRED_DEF_ID_EXAMPLE,
        },
    )


class CreateRevRegTxnForEndorserOptionSchema(OpenAPISchema):
    """Class for user to input whether to create a transaction for endorser or not."""

    create_transaction_for_endorser = fields.Boolean(
        required=False,
        metadata={"description": "Create Transaction For Endorser's signature"},
    )


class RevRegConnIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    conn_id = fields.Str(
        required=False,
        metadata={"description": "Connection identifier", "example": UUID4_EXAMPLE},
    )


class PublishRevocationsOptions(OpenAPISchema):
    """Options for publishing revocations to ledger."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,  # noqa: F821
            "required": False,
            "example": UUIDFour.EXAMPLE,
        }
    )

    create_transaction_for_endorser = fields.Bool(
        metadata={
            "description": create_transaction_for_endorser_description,
            "required": False,
            "example": False,
        }
    )


class PublishRevocationsSchemaAnoncreds(OpenAPISchema):
    """Request and result schema for revocation publication API call."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": INDY_REV_REG_ID_EXAMPLE}),
        values=fields.List(
            fields.Str(
                validate=INDY_CRED_REV_ID_VALIDATE,
                metadata={
                    "description": "Credential revocation identifier",
                    "example": INDY_CRED_REV_ID_EXAMPLE,
                },
            )
        ),
        metadata={"description": "Credential revocation ids by revocation registry id"},
    )
    options = fields.Nested(PublishRevocationsOptions())


class PublishRevocationsResultSchemaAnoncreds(OpenAPISchema):
    """Result schema for credential definition send request."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": INDY_REV_REG_ID_EXAMPLE}),
        values=fields.List(
            fields.Str(
                validate=INDY_CRED_REV_ID_VALIDATE,
                metadata={
                    "description": "Credential revocation identifier",
                    "example": INDY_CRED_REV_ID_EXAMPLE,
                },
            )
        ),
        metadata={"description": "Credential revocation ids by revocation registry id"},
    )


class RevokeRequestSchemaAnoncreds(CredRevRecordQueryStringSchema):
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
        required=False,
        metadata={
            "description": (
                "(True) publish revocation to ledger immediately, or (default, False)"
                " mark it pending"
            )
        },
    )
    notify = fields.Boolean(
        required=False,
        metadata={"description": "Send a notification to the credential recipient"},
    )
    notify_version = fields.String(
        validate=validate.OneOf(["v1_0", "v2_0"]),
        required=False,
        metadata={
            "description": (
                "Specify which version of the revocation notification should be sent"
            )
        },
    )
    connection_id = fields.Str(
        required=False,
        validate=UUID4_VALIDATE,
        metadata={
            "description": (
                "Connection ID to which the revocation notification will be sent;"
                " required if notify is true"
            ),
            "example": UUID4_EXAMPLE,
        },
    )
    thread_id = fields.Str(
        required=False,
        metadata={
            "description": (
                "Thread ID of the credential exchange message thread resulting in the"
                " credential now being revoked; required if notify is true"
            )
        },
    )
    comment = fields.Str(
        required=False,
        metadata={
            "description": "Optional comment to include in revocation notification"
        },
    )
    options = PublishRevocationsOptions()


@docs(
    tags=[TAG_TITLE],
    summary="Revoke an issued credential",
)
@request_schema(RevokeRequestSchemaAnoncreds())
@response_schema(RevocationAnoncredsModuleResponseSchema(), description="")
async def revoke(request: web.BaseRequest):
    """Request handler for storing a credential revocation.

    Args:
        request: aiohttp request object

    Returns:
        The credential revocation details.

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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

    rev_manager = RevocationManager(profile)
    try:
        if cred_ex_id:
            # rev_reg_id and cred_rev_id should not be present so we can
            # safely splat the body
            await rev_manager.revoke_credential_by_cred_ex_id(**body)
        else:
            # no cred_ex_id so we can safely splat the body
            await rev_manager.revoke_credential(**body)
        return web.json_response({})
    except (
        RevocationManagerError,
        AnonCredsRevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRegistrationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(tags=[TAG_TITLE], summary="Publish pending revocations to ledger")
@request_schema(PublishRevocationsSchemaAnoncreds())
@response_schema(PublishRevocationsResultSchemaAnoncreds(), 200, description="")
async def publish_revocations(request: web.BaseRequest):
    """Request handler for publishing pending revocations to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        Credential revocation ids published as revoked by revocation registry id.

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    body = await request.json()
    options = body.get("options", {})
    rrid2crid = body.get("rrid2crid")

    rev_manager = RevocationManager(profile)

    try:
        rev_reg_resp = await rev_manager.publish_pending_revocations(rrid2crid, options)
        return web.json_response({"rrid2crid": rev_reg_resp})
    except (
        RevocationError,
        StorageError,
        AnonCredsIssuerError,
        AnonCredsRevocationError,
    ) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err


@docs(
    tags=[TAG_TITLE],
    summary="Search for matching revocation registries that current agent created",
)
@querystring_schema(RevRegsCreatedQueryStringSchema())
@response_schema(RevRegsCreatedSchemaAnoncreds(), 200, description="")
async def get_rev_regs(request: web.BaseRequest):
    """Request handler to get revocation registries that current agent created.

    Args:
        request: aiohttp request object

    Returns:
        List of identifiers of matching revocation registries.

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    search_tags = list(vars(RevRegsCreatedQueryStringSchema)["_declared_fields"])
    tag_filter = {
        tag: request.query[tag] for tag in search_tags if tag in request.query
    }
    cred_def_id = tag_filter.get("cred_def_id")
    state = tag_filter.get("state")
    try:
        revocation = AnonCredsRevocation(profile)
        found = await revocation.get_created_revocation_registry_definitions(
            cred_def_id, state
        )
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e
    # TODO remove state == init
    return web.json_response({"rev_reg_ids": found})


@docs(
    tags=[TAG_TITLE],
    summary="Get revocation registry by revocation registry id",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegResultSchemaAnoncreds(), 200, description="")
async def get_rev_reg(request: web.BaseRequest):
    """Request handler to get a revocation registry by rev reg id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)

    return web.json_response({"result": rev_reg.serialize()})


async def _get_issuer_rev_reg_record(
    profile: AskarAnoncredsProfile, rev_reg_id
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
    tags=[TAG_TITLE],
    summary="Get current active revocation registry by credential definition id",
)
@match_info_schema(RevocationCredDefIdMatchInfoSchema())
@response_schema(RevRegResultSchemaAnoncreds(), 200, description="")
async def get_active_rev_reg(request: web.BaseRequest):
    """Request handler to get current active revocation registry by cred def id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry identifier

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    cred_def_id = request.match_info["cred_def_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        active_reg = await revocation.get_or_create_active_registry(cred_def_id)
        rev_reg = await _get_issuer_rev_reg_record(profile, active_reg.rev_reg_def_id)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({"result": rev_reg.serialize()})


@docs(tags=[TAG_TITLE], summary="Rotate revocation registry")
@match_info_schema(RevocationCredDefIdMatchInfoSchema())
@response_schema(RevRegsCreatedSchemaAnoncreds(), 200, description="")
async def rotate_rev_reg(request: web.BaseRequest):
    """Request handler to rotate the active revocation registries for cred. def.

    Args:
        request: aiohttp request object

    Returns:
        list or revocation registry ids that were rotated out

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    cred_def_id = request.match_info["cred_def_id"]

    try:
        revocation = AnonCredsRevocation(profile)
        recs = await revocation.decommission_registry(cred_def_id)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    return web.json_response({"rev_reg_ids": [rec.name for rec in recs if rec.name]})


@docs(
    tags=[TAG_TITLE],
    summary="Get number of credentials issued against revocation registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevRegIssuedResultSchemaAnoncreds(), 200, description="")
async def get_rev_reg_issued_count(request: web.BaseRequest):
    """Request handler to get number of credentials issued against revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials issued against revocation registry

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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

    async with profile.session() as session:
        count = len(
            await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
        )

    return web.json_response({"result": count})


@docs(
    tags=[TAG_TITLE],
    summary="Get details of credentials issued against revocation registry",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(CredRevRecordDetailsResultSchemaAnoncreds(), 200, description="")
async def get_rev_reg_issued(request: web.BaseRequest):
    """Request handler to get credentials issued against revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials issued against revocation registry

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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

    async with profile.session() as session:
        recs = await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
    results = []
    for rec in recs:
        results.append(rec.serialize())

    return web.json_response(results)


@docs(
    tags=[TAG_TITLE],
    summary="Get details of revoked credentials from ledger",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(CredRevIndyRecordsResultSchemaAnoncreds(), 200, description="")
async def get_rev_reg_indy_recs(request: web.BaseRequest):
    """Request handler to get details of revoked credentials from ledger.

    Args:
        request: aiohttp request object

    Returns:
        Details of revoked credentials from ledger

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    indy_registry = LegacyIndyRegistry()

    if await indy_registry.supports(rev_reg_id):
        try:
            rev_reg_delta, _ts = await indy_registry.get_revocation_registry_delta(
                profile, rev_reg_id, None
            )
        except (AnonCredsObjectNotFound, AnonCredsResolutionError) as e:
            raise web.HTTPInternalServerError(reason=str(e)) from e

        return web.json_response(
            {
                "rev_reg_delta": rev_reg_delta,
            }
        )

    raise web.HTTPInternalServerError(
        reason="Indy registry does not support revocation registry "
        f"identified by {rev_reg_id}"
    )


@docs(
    tags=[TAG_TITLE],
    summary="Fix revocation state in wallet and return number of updated entries",
)
@match_info_schema(RevRegIdMatchInfoSchema())
@querystring_schema(RevRegUpdateRequestMatchInfoSchema())
@response_schema(RevRegWalletUpdatedResultSchemaAnoncreds(), 200, description="")
async def update_rev_reg_revoked_state(request: web.BaseRequest):
    """Request handler to fix ledger entry of credentials revoked against registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials posted to ledger

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]

    apply_ledger_update_json = request.query.get("apply_ledger_update", "false")
    LOGGER.debug(">>> apply_ledger_update_json = %s", apply_ledger_update_json)
    apply_ledger_update = json.loads(request.query.get("apply_ledger_update", "false"))

    genesis_transactions = None
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason="No rev reg def found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    async with profile.session() as session:
        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        if not genesis_transactions:
            ledger_manager = context.injector.inject(BaseMultipleLedgerManager)
            write_ledger = context.injector.inject(BaseLedger)
            available_write_ledgers = await ledger_manager.get_write_ledgers()
            LOGGER.debug(f"available write_ledgers = {available_write_ledgers}")
            LOGGER.debug(f"write_ledger = {write_ledger}")
            pool = write_ledger.pool
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

    rev_manager = RevocationManager(profile)
    try:
        (
            rev_reg_delta,
            recovery_txn,
            applied_txn,
        ) = await rev_manager.update_rev_reg_revoked_state(
            rev_reg_def_id=rev_reg_id,
            apply_ledger_update=apply_ledger_update,
            genesis_transactions=genesis_transactions,
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
    tags=[TAG_TITLE],
    summary="Get credential revocation status",
)
@querystring_schema(CredRevRecordQueryStringSchema())
@response_schema(CredRevRecordResultSchemaAnoncreds(), 200, description="")
async def get_cred_rev_record(request: web.BaseRequest):
    """Request handler to get credential revocation record.

    Args:
        request: aiohttp request object

    Returns:
        The issuer credential revocation record

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.query.get("rev_reg_id")
    cred_rev_id = request.query.get("cred_rev_id")  # numeric string
    cred_ex_id = request.query.get("cred_ex_id")

    try:
        async with profile.session() as session:
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
    tags=[TAG_TITLE],
    summary="Download tails file",
    produces=["application/octet-stream"],
)
@match_info_schema(RevRegIdMatchInfoSchema())
@response_schema(RevocationAnoncredsModuleResponseSchema, description="tails file")
async def get_tails_file(request: web.BaseRequest) -> web.FileResponse:
    """Request handler to download tails file for revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        The tails file in FileResponse

    """
    #
    # there is no equivalent of this in anoncreds.
    # do we need it there or is this only for transitions.
    #
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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


@docs(tags=[TAG_TITLE], summary="Set revocation registry state manually")
@match_info_schema(RevRegIdMatchInfoSchema())
@querystring_schema(SetRevRegStateQueryStringSchema())
@response_schema(RevRegResultSchemaAnoncreds(), 200, description="")
async def set_rev_reg_state(request: web.BaseRequest):
    """Request handler to set a revocation registry state manually.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry record, updated

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

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


class TailsDeleteResponseSchema(OpenAPISchema):
    """Return schema for tails deletion."""

    message = fields.Str()


async def register(app: web.Application):
    """Register routes."""
    app.add_routes(
        [
            web.post("/anoncreds/revocation/revoke", revoke),
            web.post("/anoncreds/revocation/publish-revocations", publish_revocations),
            web.get(
                "/anoncreds/revocation/credential-record",
                get_cred_rev_record,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/registries",
                get_rev_regs,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}",
                get_rev_reg,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/active-registry/{cred_def_id}",
                get_active_rev_reg,
                allow_head=False,
            ),
            web.post(
                "/anoncreds/revocation/active-registry/{cred_def_id}/rotate",
                rotate_rev_reg,
            ),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}/issued",
                get_rev_reg_issued_count,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}/issued/details",
                get_rev_reg_issued,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}/issued/indy_recs",
                get_rev_reg_indy_recs,
                allow_head=False,
            ),
            web.get(
                "/anoncreds/revocation/registry/{rev_reg_id}/tails-file",
                get_tails_file,
                allow_head=False,
            ),
            web.patch(
                "/anoncreds/revocation/registry/{rev_reg_id}/set-state",
                set_rev_reg_state,
            ),
            web.put(
                "/anoncreds/revocation/registry/{rev_reg_id}/fix-revocation-entry-state",
                update_rev_reg_revoked_state,
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
            "name": TAG_TITLE,
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
