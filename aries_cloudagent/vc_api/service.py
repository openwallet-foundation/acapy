"""VC-API Service for interacting with the VcLdpManager."""

from aiohttp import web

from ..vc.vc_ld.manager import VcLdpManager as VcManager
from ..vc.vc_ld.manager import VcLdpManagerError as VcManagerError
from ..admin.request_context import AdminRequestContext
from ..config.base import InjectionError
from ..resolver.base import ResolverError
from ..wallet.error import WalletError
from ..storage.error import StorageError, StorageNotFoundError
from ..storage.vc_holder.base import VCHolder

from ..vc.vc_ld.models.credential import (
    VerifiableCredential,
)

from ..vc.vc_ld.models.presentation import (
    VerifiablePresentation,
)

from ..vc.vc_ld.models.options import LDProofVCOptions


async def list_stored_credentials(request):
    """List stored credentials.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        list: Stored verifiable credentials

    """
    context: AdminRequestContext = request["context"]
    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
    try:
        search = holder.search_credentials()
        records = await search.fetch()
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return records


async def fetch_stored_credential(request):
    """Fetch stored credential by id.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        VerifiableCredential: A stored verifiable credential

    """
    context: AdminRequestContext = request["context"]
    credential_id = request.match_info["credential_id"]
    async with context.profile.session() as session:
        holder = session.inject(VCHolder)
    try:
        search = holder.search_credentials(given_id=credential_id.strip('"'))
        records = await search.fetch()
        record = [record.serialize() for record in records]
        credential = record[0]["cred_value"] if len(record) == 1 else None
    except StorageNotFoundError as err:
        raise web.HTTPNotFound(reason=err.roll_up) from err
    except StorageError as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err
    return credential


async def issue_credential(request):
    """Issue credential.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        VerifiableCredential: A verifiable credential

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    credential = body["credential"]
    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2020 if no proof type is provided
    options["proofType"] = (
        options.pop("type") if "type" in options else "Ed25519Signature2018"
    )
    try:
        credential = VerifiableCredential.deserialize(credential)
        options = LDProofVCOptions.deserialize(options)
        manager = context.inject(VcManager)
        vc = await manager.issue(credential, options)
    except VcManagerError as err:
        raise web.HTTPBadRequest(reason=str(err))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return vc


async def store_issued_credential(request):
    """Store issued credential.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        Bool: If the credential has been stored.

    """
    body = await request.json()
    vc = body["verifiableCredential"]
    options = {} if "options" not in body else body["options"]

    try:
        vc = VerifiableCredential.deserialize(vc)
        options = LDProofVCOptions.deserialize(options)
        context: AdminRequestContext = request["context"]
        manager = context.inject(VcManager)
        await manager.verify_credential(vc)
        await manager.store_credential(vc, options)
    except VcManagerError as err:
        raise web.HTTPBadRequest(reason=str(err))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="Bad credential")
    return True


async def verify_credential(request):
    """Verify credential.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        PresentationVerificationResultSchema: Results of the verification.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vc = body.get("verifiableCredential")
    options = {} if "options" not in body else body["options"]
    try:
        vc = VerifiableCredential.deserialize(vc)
        options = LDProofVCOptions.deserialize(options)
        manager = context.inject(VcManager)
        result = await manager.verify_credential(vc)
    except (VcManagerError, ResolverError, ValueError) as error:
        raise web.HTTPBadRequest(reason=str(error))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return result


async def prove_presentation(request):
    """Prove presentation.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        VerifiablePresentation: verifiable presentation.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    presentation = body["presentation"]
    options = {} if "options" not in body else body["options"]
    # Default to Ed25519Signature2020 if no proof type is provided
    options["proofType"] = (
        options.pop("type") if "type" in options else "Ed25519Signature2018"
    )

    try:
        presentation = VerifiablePresentation.deserialize(presentation)
        options = LDProofVCOptions.deserialize(options)
        manager = context.inject(VcManager)
        vp = await manager.prove(presentation, options)
    except VcManagerError as err:
        raise web.HTTPBadRequest(reason=str(err))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return vp


async def verify_presentation(request):
    """Verify presentation.

    Process the web request and pass it to the VcLdpManage.

    Args:
        request (web.BaseRequest): aiohttp web request object.

    Returns:
        PresentationVerificationResultSchema: Results of the verification.

    """
    context: AdminRequestContext = request["context"]
    body = await request.json()
    vp = body.get("verifiablePresentation")
    options = {} if "options" not in body else body["options"]
    try:
        vp = VerifiablePresentation.deserialize(vp)
        options = LDProofVCOptions.deserialize(options)
        manager = context.inject(VcManager)
        result = await manager.verify_presentation(vp, options)
    except (VcManagerError, ResolverError, ValueError) as err:
        raise web.HTTPBadRequest(reason=str(err))
    except (WalletError, InjectionError):
        raise web.HTTPForbidden(reason="No wallet available")
    return result
