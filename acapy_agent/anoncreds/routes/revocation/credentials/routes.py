"""AnonCreds credential revocation routes."""

import logging

from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
    response_schema,
)

from .....admin.decorators.auth import tenant_authentication
from .....admin.request_context import AdminRequestContext
from .....revocation.error import RevocationError
from .....storage.error import StorageDuplicateError, StorageError, StorageNotFoundError
from .....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ....base import AnonCredsRegistrationError
from ....issuer import AnonCredsIssuerError
from ....models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
)
from ....revocation import AnonCredsRevocationError
from ....revocation.manager import RevocationManager, RevocationManagerError
from ....routes.revocation import AnonCredsRevocationModuleResponseSchema
from ...common.utils import get_request_body_with_profile_check
from .. import REVOCATION_TAG_TITLE
from .models import (
    CredRevRecordQueryStringSchema,
    CredRevRecordResultSchemaAnonCreds,
    PublishRevocationsResultSchemaAnonCreds,
    PublishRevocationsSchemaAnonCreds,
    RevokeRequestSchemaAnonCreds,
)

LOGGER = logging.getLogger(__name__)


@docs(
    tags=[REVOCATION_TAG_TITLE],
    summary="Revoke an issued credential",
)
@request_schema(RevokeRequestSchemaAnonCreds())
@response_schema(AnonCredsRevocationModuleResponseSchema(), description="")
@tenant_authentication
async def revoke(request: web.BaseRequest):
    """Request handler for storing a credential revocation.

    Args:
        request: aiohttp request object

    Returns:
        The credential revocation details.

    """
    context, profile, body, _ = await get_request_body_with_profile_check(request)
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


@docs(tags=[REVOCATION_TAG_TITLE], summary="Publish pending revocations to ledger")
@request_schema(PublishRevocationsSchemaAnonCreds())
@response_schema(PublishRevocationsResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
async def publish_revocations(request: web.BaseRequest):
    """Request handler for publishing pending revocations to the ledger.

    Args:
        request: aiohttp request object

    Returns:
        Credential revocation ids published as revoked by revocation registry id.

    """
    _, profile, body, options = await get_request_body_with_profile_check(request)
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
    tags=[REVOCATION_TAG_TITLE],
    summary="Get credential revocation status",
)
@querystring_schema(CredRevRecordQueryStringSchema())
@response_schema(CredRevRecordResultSchemaAnonCreds(), 200, description="")
@tenant_authentication
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
                recs = await IssuerCredRevRecord.retrieve_by_ids(
                    session, rev_reg_id, cred_rev_id
                )
                if len(recs) == 1:
                    rec = recs[0]
                elif len(recs) > 1:
                    raise StorageDuplicateError(
                        f"Multiple records found for rev_reg_id: {rev_reg_id} "
                        f"and cred_rev_id: {cred_rev_id}"
                    )
                else:
                    raise StorageNotFoundError(
                        f"No record found for rev_reg_id: {rev_reg_id} "
                        f"and cred_rev_id: {cred_rev_id}"
                    )
            else:
                rec = await IssuerCredRevRecord.retrieve_by_cred_ex_id(
                    session, cred_ex_id
                )
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err

    return web.json_response({"result": rec.serialize()})


async def register(app: web.Application) -> None:
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
