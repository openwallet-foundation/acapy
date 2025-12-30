"""AnonCreds revocation registry routes."""

import json
import logging
from asyncio import shield

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)
from uuid_utils import uuid4

from .....admin.decorators.auth import tenant_authentication
from .....admin.request_context import AdminRequestContext
from .....askar.profile_anon import AskarAnonCredsProfile
from .....indy.issuer import IndyIssuerError
from .....indy.models.revocation import IndyRevRegDef
from .....ledger.base import BaseLedger
from .....ledger.error import LedgerError
from .....ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from .....revocation.error import RevocationError
from .....revocation.models.issuer_rev_reg_record import (
    IssuerRevRegRecord,
)
from .....storage.error import StorageError
from .....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ....base import AnonCredsObjectNotFound, AnonCredsResolutionError
from ....default.legacy_indy.registry import LegacyIndyRegistry
from ....issuer import AnonCredsIssuer, AnonCredsIssuerError
from ....models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
)
from ....models.revocation import RevRegDefResultSchema
from ....revocation import AnonCredsRevocation, AnonCredsRevocationError
from ....revocation.manager import RevocationManager, RevocationManagerError
from ....routes.revocation import AnonCredsRevocationModuleResponseSchema
from ....util import handle_value_error
from ...common.utils import (
    get_request_body_with_profile_check,
    get_revocation_registry_definition_or_404,
)
from .. import REVOCATION_TAG_TITLE
from .models import (
    AnonCredsRevRegIdMatchInfoSchema,
    CredRevRecordDetailsResultSchemaAnonCreds,
    CredRevRecordsResultSchemaAnonCreds,
    RevocationCredDefIdMatchInfoSchema,
    RevRegCreateRequestSchemaAnonCreds,
    RevRegIssuedResultSchemaAnonCreds,
    RevRegResultSchemaAnonCreds,
    RevRegsCreatedQueryStringSchema,
    RevRegsCreatedSchemaAnonCreds,
    RevRegUpdateRequestMatchInfoSchema,
    RevRegWalletUpdatedResultSchemaAnonCreds,
    SetRevRegStateQueryStringSchema,
)

LOGGER = logging.getLogger(__name__)


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Create and publish a revocation registry definition on the connected datastore",  # noqa: E501
)
@request_schema(RevRegCreateRequestSchemaAnonCreds())
@response_schema(RevRegDefResultSchema(), 200, description="")
@tenant_authentication
async def rev_reg_def_post(request: web.BaseRequest):
    """Request handler for creating revocation registry definition."""
    _, profile, body, options = await get_request_body_with_profile_check(request)
    revocation_registry_definition = body.get("revocation_registry_definition")

    if revocation_registry_definition is None:
        raise web.HTTPBadRequest(
            reason="revocation_registry_definition object is required"
        )

    issuer_id = revocation_registry_definition.get("issuerId")
    cred_def_id = revocation_registry_definition.get("credDefId")
    max_cred_num = revocation_registry_definition.get("maxCredNum")
    tag = revocation_registry_definition.get("tag")

    issuer = AnonCredsIssuer(profile)
    revocation = AnonCredsRevocation(profile)
    # check we published this cred def
    found = await issuer.match_created_credential_definitions(cred_def_id)
    if not found:
        raise web.HTTPNotFound(
            reason=f"Not issuer of credential definition id {cred_def_id}"
        )

    result = await shield(
        revocation.create_and_register_revocation_registry_definition(
            issuer_id,
            cred_def_id,
            registry_type="CL_ACCUM",
            max_cred_num=max_cred_num,
            tag=tag,
            options=options,
        )
    )
    if isinstance(result, str):  # if it's a string, it's an error message
        raise web.HTTPBadRequest(reason=result)

    return web.json_response(result.serialize())


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Update the active registry",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(AnonCredsRevocationModuleResponseSchema(), description="")
@tenant_authentication
async def set_active_registry(request: web.BaseRequest):
    """Request handler to set the active registry.

    Args:
        request: aiohttp request object

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    try:
        revocation = AnonCredsRevocation(profile)
        await revocation.set_active_registry(rev_reg_id)
        return web.json_response({})
    except ValueError as e:
        handle_value_error(e)
    except AnonCredsRevocationError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Search for matching revocation registries that current agent created",
)
@querystring_schema(RevRegsCreatedQueryStringSchema())
@response_schema(RevRegsCreatedSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
    tag_filter = {tag: request.query[tag] for tag in search_tags if tag in request.query}
    cred_def_id = tag_filter.get("cred_def_id")
    state = tag_filter.get("state")
    try:
        revocation = AnonCredsRevocation(profile)
        found = await revocation.get_created_revocation_registry_definitions(
            cred_def_id, state
        )
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e
    return web.json_response({"rev_reg_ids": found})


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Get revocation registry by revocation registry id",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(RevRegResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
async def get_rev_reg(request: web.BaseRequest):
    """Request handler to get a revocation registry by rev reg id.

    Args:
        request: aiohttp request object

    Returns:
        The revocation registry identifier

    """
    context: AdminRequestContext = request["context"]
    profile = context.profile

    is_not_anoncreds_profile_raise_web_exception(profile)

    rev_reg_id = request.match_info["rev_reg_id"]
    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)

    return web.json_response({"result": rev_reg.serialize()})


async def _get_issuer_rev_reg_record(
    profile: AskarAnonCredsProfile, rev_reg_id: str
) -> IssuerRevRegRecord:
    # fetch rev reg def from anoncreds
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason=f"Rev reg def with id {rev_reg_id} not found")
        # looking good, so grab some other data
        state = await revocation.get_created_revocation_registry_definition_state(
            rev_reg_id
        )
        pending_pubs = await revocation.get_pending_revocations(rev_reg_id)
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    # transform
    result = IssuerRevRegRecord(
        record_id=uuid4(),
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
    tags=[REVOCATION_TAG_TITLE],
    summary="Get current active revocation registry by credential definition id",
)
@match_info_schema(RevocationCredDefIdMatchInfoSchema())
@response_schema(RevRegResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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


@docs(tags=[REVOCATION_TAG_TITLE], summary="Rotate revocation registry")
@match_info_schema(RevocationCredDefIdMatchInfoSchema())
@response_schema(RevRegsCreatedSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
    tags=[REVOCATION_TAG_TITLE],
    summary="Get number of credentials issued against revocation registry",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(RevRegIssuedResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
async def get_rev_reg_issued_count(request: web.BaseRequest):
    """Request handler to get number of credentials issued against revocation registry.

    Args:
        request: aiohttp request object

    Returns:
        Number of credentials issued against revocation registry

    """
    _, rev_reg_id = await get_revocation_registry_definition_or_404(request)

    async with request["context"].profile.session() as session:
        count = len(
            await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
        )

    return web.json_response({"result": count})


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Get details of credentials issued against revocation registry",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(CredRevRecordDetailsResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
            raise web.HTTPNotFound(reason=f"Rev reg def with id {rev_reg_id} not found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    async with profile.session() as session:
        recs = await IssuerCredRevRecord.query_by_ids(session, rev_reg_id=rev_reg_id)
    results = []
    for rec in recs:
        results.append(rec.serialize())

    return web.json_response(results)


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Get details of revoked credentials from ledger",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(CredRevRecordsResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
    tags=[REVOCATION_TAG_TITLE],
    summary="Fix revocation state in wallet and return number of updated entries",
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@querystring_schema(RevRegUpdateRequestMatchInfoSchema())
@response_schema(RevRegWalletUpdatedResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
    apply_ledger_update = json.loads(request.query.get("apply_ledger_update", "false"))
    LOGGER.debug(
        "Update revocation state request for rev_reg_id = %s, apply_ledger_update = %s",
        rev_reg_id,
        apply_ledger_update,
    )

    genesis_transactions = None
    recovery_txn = {}
    try:
        revocation = AnonCredsRevocation(profile)
        rev_reg_def = await revocation.get_created_revocation_registry_definition(
            rev_reg_id
        )
        if rev_reg_def is None:
            raise web.HTTPNotFound(reason=f"Rev reg def with id {rev_reg_id} not found")
    except AnonCredsIssuerError as e:
        raise web.HTTPInternalServerError(reason=str(e)) from e

    async with profile.session() as session:
        genesis_transactions = context.settings.get("ledger.genesis_transactions")
        if not genesis_transactions:
            ledger_manager = context.injector.inject(BaseMultipleLedgerManager)
            write_ledger = context.injector.inject(BaseLedger)
            available_write_ledgers = await ledger_manager.get_write_ledgers()
            LOGGER.debug("available write_ledgers = %s", available_write_ledgers)
            LOGGER.debug("write_ledger = %s", write_ledger)
            pool = write_ledger.pool
            LOGGER.debug("write_ledger pool = %s", pool)

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
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    except Exception as err:
        LOGGER.exception(f"Error updating revocation registry revoked state: {err}")
        raise web.HTTPInternalServerError(reason=str(err)) from err

    return web.json_response(
        {
            "rev_reg_delta": rev_reg_delta,
            "recovery_txn": recovery_txn,
            "applied_txn": applied_txn,
        }
    )


@docs(tags=[REVOCATION_TAG_TITLE], summary="Set revocation registry state manually")
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@querystring_schema(SetRevRegStateQueryStringSchema())
@response_schema(RevRegResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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

    rev_reg_id: str = request.match_info["rev_reg_id"]
    state: str = request.query["state"]  # required in query string schema

    try:
        revocation = AnonCredsRevocation(profile)
        await revocation.set_rev_reg_state(rev_reg_id, state)

    except AnonCredsRevocationError as e:
        if "not found" in str(e):
            raise web.HTTPNotFound(reason=str(e)) from e
        raise web.HTTPInternalServerError(reason=str(e)) from e

    rev_reg = await _get_issuer_rev_reg_record(profile, rev_reg_id)
    return web.json_response({"result": rev_reg.serialize()})


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Update the active registry",
    deprecated=True,
)
@match_info_schema(AnonCredsRevRegIdMatchInfoSchema())
@response_schema(AnonCredsRevocationModuleResponseSchema(), description="")
@tenant_authentication
async def set_active_registry_deprecated(request: web.BaseRequest):
    """Deprecated alias for set_active_registry."""
    return await set_active_registry(request)


async def register(app: web.Application) -> None:
    """Register routes."""
    app.add_routes(
        [
            web.post("/anoncreds/revocation-registry-definition", rev_reg_def_post),
            web.put(
                "/anoncreds/registry/{rev_reg_id}/active", set_active_registry_deprecated
            ),
            web.put(
                "/anoncreds/revocation/registry/{rev_reg_id}/active", set_active_registry
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


def post_process_routes(app: web.Application) -> None:
    """Amend swagger API."""
    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": REVOCATION_TAG_TITLE,
            "description": "AnonCreds revocation registry management",
            "externalDocs": {
                "description": "Overview",
                "url": "https://github.com/hyperledger/indy-hipe/tree/master/text/0011-cred-revocation",
            },
        }
    )
