"""AnonCreds credential revocation routes."""

import logging

from aiohttp import web
from aiohttp_apispec import (
    docs,
    querystring_schema,
    request_schema,
    response_schema,
)
from marshmallow import fields, validate, validates_schema
from marshmallow.exceptions import ValidationError

from .....admin.decorators.auth import tenant_authentication
from .....admin.request_context import AdminRequestContext
from .....anoncreds.base import AnonCredsRegistrationError
from .....anoncreds.issuer import AnonCredsIssuerError
from .....anoncreds.revocation import AnonCredsRevocationError
from .....anoncreds.routes.revocation import AnonCredsRevocationModuleResponseSchema
from .....messaging.models.openapi import OpenAPISchema
from .....messaging.valid import (
    ANONCREDS_CRED_REV_ID_EXAMPLE,
    ANONCREDS_CRED_REV_ID_VALIDATE,
    ANONCREDS_REV_REG_ID_EXAMPLE,
    ANONCREDS_REV_REG_ID_VALIDATE,
    UUID4_EXAMPLE,
    UUID4_VALIDATE,
    UUIDFour,
)
from .....revocation.error import RevocationError
from .....storage.error import StorageDuplicateError, StorageError, StorageNotFoundError
from .....utils.profiles import is_not_anoncreds_profile_raise_web_exception
from ....models.issuer_cred_rev_record import (
    IssuerCredRevRecord,
    IssuerCredRevRecordSchemaAnonCreds,
)
from ....revocation.manager import RevocationManager, RevocationManagerError
from ...common import (
    create_transaction_for_endorser_description,
    endorser_connection_id_description,
)
from .. import REVOCATION_TAG_TITLE

LOGGER = logging.getLogger(__name__)


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
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )
    cred_rev_id = fields.Str(
        required=False,
        validate=ANONCREDS_CRED_REV_ID_VALIDATE,
        metadata={
            "description": "Credential revocation identifier",
            "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
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


class CredRevRecordResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for credential revocation record request."""

    result = fields.Nested(IssuerCredRevRecordSchemaAnonCreds())


class PublishRevocationsOptions(OpenAPISchema):
    """Options for publishing revocations to ledger."""

    endorser_connection_id = fields.Str(
        metadata={
            "description": endorser_connection_id_description,
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


class PublishRevocationsSchemaAnonCreds(OpenAPISchema):
    """Request and result schema for revocation publication API call."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": ANONCREDS_REV_REG_ID_EXAMPLE}),
        values=fields.List(
            fields.Str(
                validate=ANONCREDS_CRED_REV_ID_VALIDATE,
                metadata={
                    "description": "Credential revocation identifier",
                    "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
                },
            )
        ),
        metadata={"description": "Credential revocation ids by revocation registry id"},
    )
    options = fields.Nested(PublishRevocationsOptions())


class PublishRevocationsResultSchemaAnonCreds(OpenAPISchema):
    """Result schema for credential definition send request."""

    rrid2crid = fields.Dict(
        required=False,
        keys=fields.Str(metadata={"example": ANONCREDS_REV_REG_ID_EXAMPLE}),
        values=fields.List(
            fields.Str(
                validate=ANONCREDS_CRED_REV_ID_VALIDATE,
                metadata={
                    "description": "Credential revocation identifier",
                    "example": ANONCREDS_CRED_REV_ID_EXAMPLE,
                },
            )
        ),
        metadata={"description": "Credential revocation ids by revocation registry id"},
    )


class RevokeRequestSchemaAnonCreds(CredRevRecordQueryStringSchema):
    """Parameters and validators for revocation request."""

    @validates_schema
    def validate_fields(self, data, **kwargs):
        """Validate fields - connection_id and thread_id must be present if notify."""
        super().validate_fields(data, **kwargs)

        notify = data.get("notify")
        connection_id = data.get("connection_id")
        notify_version = data.get("notify_version", "v1_0")

        if notify and not connection_id:
            raise ValidationError("Request must specify connection_id if notify is true")
        if notify and not notify_version:
            raise ValidationError("Request must specify notify_version if notify is true")

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


class AnonCredsRevRegIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking rev reg id."""

    rev_reg_id = fields.Str(
        required=True,
        validate=ANONCREDS_REV_REG_ID_VALIDATE,
        metadata={
            "description": "Revocation Registry identifier",
            "example": ANONCREDS_REV_REG_ID_EXAMPLE,
        },
    )


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


def post_process_routes(app: web.Application):
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
