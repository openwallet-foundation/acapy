import asyncio
import logging
import math
import os
import time

from aiohttp import web
import django.db
import jsonschema

from vonx.indy.messages import (
    ConstructedProof as VonxConstructedProof,
    ProofRequest as VonxProofRequest,
)
from vonx.indy.errors import IndyError

from vonx.web.headers import (
    KeyCache,
    KeyFinderBase,
    IndyKeyFinder,
)
from vonx.web.view_helpers import (
    IndyRequestError,
    check_request_signature,
    get_request_did,
    get_request_json,
    perform_store_credential,
)
import vonx.web.views as vonx_views

from api_v2.models.User import User

from api_v2.models.Credential import Credential as CredentialModel

from api_indy.indy.issuer import IssuerManager, IssuerException
from api_indy.indy.proof_request import ProofRequest
from api_indy.indy.proof import ProofManager

from api_v2.jsonschema.issuer import ISSUER_JSON_SCHEMA

from api_indy.tob_anchor.boot import (
    indy_client, indy_holder_id, run_django
)

LOGGER = logging.getLogger(__name__)

INSTRUMENT = True
STATS = {"min": {}, "max": {}, "total": {}, "count": {}}

INDY_KEYFINDER = None
DJANGO_KEYFINDER = None
KEY_CACHE = None


class DjangoKeyFinder(KeyFinderBase):
    """
    Handle public key lookup for the issuer's DID
    """
    async def _lookup_key(self, key_id: str, key_type: str) -> bytes:
        if key_type == "ed25519":
            return await run_django(self._db_lookup, key_id)

    def _db_lookup(self, key_id: str) -> bytes:
        try:
            user = User.objects.get(DID=key_id)
            if user.verkey:
                verkey = bytes(user.verkey)
                LOGGER.info(
                    "Found verkey for DID '%s' in users table: '%s'",
                    key_id, verkey)
                return verkey
        except User.DoesNotExist:
            pass

def _indy_client():
    try:
        result = indy_client()
    except RuntimeError as e:
        raise IndyRequestError(str(e)) from e
    return result

def get_key_finder(use_cache: bool = True) -> KeyFinderBase:
    global INDY_KEYFINDER, DJANGO_KEYFINDER, KEY_CACHE
    if use_cache and KEY_CACHE:
        return KEY_CACHE
    if not INDY_KEYFINDER:
        # may raise RuntimeError on indy_client() if Indy service has not been started
        INDY_KEYFINDER = IndyKeyFinder(_indy_client(), indy_holder_id())
        DJANGO_KEYFINDER = DjangoKeyFinder(INDY_KEYFINDER)
        KEY_CACHE = KeyCache(DJANGO_KEYFINDER)
    return INDY_KEYFINDER

async def _check_signature(request, use_cache: bool = True):
    """
    Check the DID-auth signature on the incoming request
    """
    perf = _time_start("check_signature")
    key_finder = get_key_finder(use_cache)
    result = await check_request_signature(request, key_finder, required=True)
    perf = _time_end(perf)
    return result

def _validate_schema(data, schema):
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as e:
        LOGGER.exception("Error validating schema:")
        raise IndyRequestError("Schema validation error: {}".format(e))

def _time_start(*tasks):
    return (tasks, time.perf_counter())

def _time_end(timer):
    (tasks, start) = timer
    diff = time.perf_counter() - start
    for task in tasks:
        STATS["min"][task] = min(STATS["min"].get(task, diff), diff)
        STATS["max"][task] = max(STATS["max"].get(task, 0), diff)
        STATS["total"][task] = STATS["total"].get(task, 0) + diff
        STATS["count"][task] = STATS["count"].get(task, 0) + 1
    return diff


async def generate_credential_request(request):
    """
    Processes a credential definition and responds with a credential request
    which can then be used to submit a credential.

    Example request payload:

    ```json
    {
        'credential_offer': <credential offer json>,
        'credential_definition': <credential definition json>
    }
    ```

    returns:

    ```
    {
        "credential_request": <credential request json>,
        "credential_request_metadata": <credential request metadata json>
    }
    ```
    """

    LOGGER.warn(">>> Generate credential request")
    perf = _time_start("generate_credential_request")

    try:
        await _check_signature(request)
        response = await vonx_views.generate_credential_request(request, indy_holder_id())
    except IndyRequestError as e:
        response = e.response

    LOGGER.warn("<<< Generate credential request: %s", _time_end(perf))

    return response


async def store_credential(request):
    """
    Stores one or more verifiable credentials in the wallet.

    The data in the credential is parsed and stored in the database
    for search/display purposes based on the issuer's processor config.
    The data is then made available through a REST API as well as a
    search API.

    Example request payload:

    ```json
    {
        "credential_data": <credential data>,
        "credential_request_metadata": <credential request metadata>
    }
    ```

    Input may also be in the form of an array of credential data:

    ```json
    [
        {
            "credential_data": <credential data>,
            "credential_request_metadata": <credential request metadata>
        },
        {
            "credential_data": <credential data>,
            "credential_request_metadata": <credential request metadata>
        }
    ]
    ```

    Returns: the wallet ID of the stored credential or credentials
    """

    LOGGER.warn(">>> Store credential")
    perf = _time_start("store_credential")

    try:
        await _check_signature(request)
        issuer_did = get_request_did(request)
        client = _indy_client()
        params = await get_request_json(request)
        processor = request.app["credqueue"] # CredentialProcessorQueue
        stored, ret = await perform_store_credential(
            client, indy_holder_id(), params, processor, issuer_did)
        response = web.json_response(ret)
        response["stored"] = stored
    except IndyRequestError as e:
        response = e.response

    LOGGER.warn("<<< Store credential: %s", _time_end(perf))

    return response


async def register_issuer(request):
    """
    Processes an issuer definition and creates or updates the
    corresponding records. Responds with the updated issuer
    definition including record IDs.

    Example request payload:

    ```json
    {
        "issuer": {
            "did": "6qnvgJtqwK44D8LFYnV5Yf", // required
            "name": "BC Corporate Registry", // required
            "abbreviation": "BCReg",
            "email": "bcreg.test.issuer@example.ca",
            "url": "http://localhost:5000"
        },
        "credential_types": [
            {
            "name": "Incorporation",
            "schema": "incorporation.bc_registries",
            "version": "1.0.31",
            "endpoint": "http://localhost:5000/bcreg/incorporation",
            "topic": {
                "source_id": {
                    "input": "corp_num",
                    "from": "claim"
                },
                "type": {
                    "input": "incorporation",
                    "from": "value"
                }
            },
            "mapping": [
                {
                "model": "name",
                "fields": {
                    "text": {
                        "input": "legal_name",
                        "from": "claim"
                    },
                    "type": {
                        "input": "legal_name",
                        "from": "value"
                    }
                }
                }
            ]
            },
            {
            "name": "Doing Business As",
            "schema": "doing_business_as.bc_registries",
            "version": "1.0.31",
            "endpoint": "http://localhost:5000/bcreg/dba",
            "topic": {
                "parent_source_id": {
                    "input": "org_registry_id",
                    "from": "claim"
                },
                "parent_type": {
                    "input": "incorporation",
                    "from": "value"
                },
                "source_id": {
                    "input": "dba_corp_num",
                    "from": "claim"
                },
                "type": {
                    "input": "doing_business_as",
                    "from": "value"
                }
            },
            "mapping": [
                {
                "model": "name",
                "fields": {
                    "text": {
                        "input": "dba_name",
                        "from": "claim"
                    },
                    "type": {
                        "input": "dba_name",
                        "from": "value"
                    }
                }
                }
            ]
            },
            {
            "name": "Corporate Address",
            "schema": "address.bc_registries",
            "version": "1.0.31",
            "endpoint": "http://localhost:5000/bcreg/address",
            "topic": [
                {
                    "parent_source_id": {
                        "input": "org_registry_id",
                        "from": "claim"
                    },
                    "parent_type": {
                        "input": "incorporation",
                        "from": "value"
                    },
                    "source_id": {
                        "input": "dba_corp_num",
                        "from": "claim"
                    },
                    "type": {
                        "input": "doing_business_as",
                        "from": "value"
                    }
                },
                {
                    "source_id": {
                        "input": "org_registry_id",
                        "from": "claim"
                    },
                    "type": {
                        "input": "incorporation",
                        "from": "value"
                    }
                }
            ],
            "cardinality_fields": ["addr_type"],
            "mapping": [
                {
                    "model": "address",
                    "fields": {
                        "addressee": {
                            "input": "addressee",
                            "from": "claim"
                        },
                        "civic_address": {
                            "input": "local_address",
                            "from": "claim"
                        },
                        "city": {
                            "input": "municipality",
                            "from": "claim"
                        },
                        "province": {
                            "input": "province",
                            "from": "claim"
                        },
                        "postal_code": {
                            "input": "postal_code",
                            "from": "claim",
                            "processor": ["string_helpers.uppercase"]
                        },
                        "country": {
                            "input": "country",
                            "from": "claim"
                        },
                        "type": {
                            "input": "addr_type",
                            "from": "claim"
                        },
                        "end_date": {
                            "input": "end_date",
                            "from": "claim"
                        }
                    }
                }
            ]
            }
        ]
        }
    ```

    returns:
    ```
    {
        "success": true,
        "result": {
            "issuer": {
                "id": 1,
                "did": "6qnvgJtqwK44D8LFYnV5Yf",
                "name": "BC Corporate Registry",
                "abbreviation": "BCReg",
                "email": "bcreg.test.issuer@example.ca",
                "url": "http://localhost:5000"
            },
            "schemas": [
                {
                    "id": 1,
                    "name": "incorporation.bc_registries",
                    "version": "1.0.31",
                    "origin_did": "6qnvgJtqwK44D8LFYnV5Yf"
                },
                {
                    "id": 2,
                    "name": "doing_business_as.bc_registries",
                    "version": "1.0.31",
                    "origin_did": "6qnvgJtqwK44D8LFYnV5Yf"
                }
            ],
            "credential_types": [
                {
                    "id": 1,
                    "schema_id": 1,
                    "issuer_id": 1,
                    "description": "Incorporation",
                    "processor_config": null
                },
                {
                    "id": 2,
                    "schema_id": 2,
                    "issuer_id": 1,
                    "description": "Doing Business As",
                    "processor_config": null
                }
            ]
        }
    }
    ```
    """

    def process(request, data):
        try:
            issuer_manager = IssuerManager()
            updated = issuer_manager.register_issuer(didauth, data)
            return {"success": True, "result": updated}
        except IssuerException as e:
            LOGGER.exception("Issuer request not accepted:")
            return {"success": False, "result": str(e)}

    LOGGER.warn(">>> Register issuer")
    perf = _time_start("register_issuer")

    try:
        # not using lookup on users table
        didauth = await _check_signature(request, False)
        data = await get_request_json(request)
        _validate_schema(data, ISSUER_JSON_SCHEMA)
        result = await run_django(process, request, data)
        if result["success"]:
            await KEY_CACHE._cache_invalidate(didauth["keyId"], didauth["algorithm"])
        response = web.json_response(result)
    except IndyRequestError as e:
        response = e.response

    LOGGER.warn("<<< Register issuer: %s", _time_end(perf))

    return response


async def construct_proof(request):
    """
    Constructs a proof given a proof request

    ```json
    {
        "proof_request": <HL Indy proof request>
    }
    ```

    returns: HL Indy proof data
    """

    LOGGER.warn(">>> Construct proof")
    perf = _time_start("construct_proof")

    try:
        await _check_signature(request)
        response = await vonx_views.construct_proof(request, indy_holder_id())
    except IndyRequestError as e:
        response = e.response

    LOGGER.warn("<<< Construct proof: %s", _time_end(perf))

    return response


async def verify_credential(request):
    """
    Constructs a proof request for a credential stored in the
    application database, constructs a proof for that proof
    request, and then verifies it.

    returns:

    ```json
    {
        "verified": <verification successful boolean>,
        "proof": <proof json>,
        "proof_request": <proof_request json>,
    }
    ```
    """
    LOGGER.warn(">>> Verify credential")
    perf = _time_start("verify_credential")
    credential_id = request.match_info.get("id")
    headers = {'Access-Control-Allow-Origin': '*'}

    if not credential_id:
        return web.json_response(
            {"success": False, "result": "Credential ID not provided"},
            status=400,
            headers=headers,
        )

    def fetch_cred(credential_id):
        try:
            return CredentialModel.objects\
                .prefetch_related('claims')\
                .select_related('credential_type')\
                .select_related('credential_type__schema')\
                .get(id=credential_id)
        except CredentialModel.DoesNotExist:
            return None
    credential = await run_django(fetch_cred, credential_id)
    if not credential:
        LOGGER.warn("Credential not found: %s", credential_id)
        return web.json_response(
            {"success": False, "result": "Credential not found"},
            status=404,
            headers=headers,
        )

    proof_request = ProofRequest(name="the-org-book", version="1.0.0")
    proof_request.build_from_credential(credential)

    proof_manager = ProofManager(proof_request.dict, {credential.wallet_id})
    try:
        proof = await proof_manager.construct_proof_async()
        verified = await _indy_client().verify_proof(
                indy_holder_id(),
                VonxProofRequest(proof_request.dict),
                VonxConstructedProof(proof))
    except IndyError as e:
        LOGGER.exception("Credential verification error:")
        return web.json_response(
            {"success": False, "result": "Credential verification error: {}".format(str(e))},
            headers=headers,
        )
    except:
        LOGGER.exception("Credential verification error:")
        return web.json_response(
            {"success": False, "result": "Not available"},
            status=403,
            headers=headers,
        )

    verified = verified.verified == "true"
    LOGGER.warn("<<< Verify credential: %s", _time_end(perf))

    return web.json_response(
        {
            "success": verified,
            "result": {
                "verified": verified,
                "proof": proof,
                "proof_request": proof_request.dict,
            },
        },
        headers=headers,
    )


async def request_info(request):
    """
    Used to debug API security
    """
    info = {
        "forwarded": repr(request.forwarded),
        "headers": dict(request.headers),
        "host": request.host,
        "path_qs": request.path_qs,
        "remote": request.remote,
        "secure": request.secure,
    }
    return web.json_response(info)


async def combined_health(request):
    """
    Combined health check including Indy and the database
    """
    ok = True
    disconnected = os.environ.get('INDY_DISABLED', 'false')
    if not disconnected or disconnected == 'false':
        try:
            result = await _indy_client().get_status()
            indy_ok = result and result.get("synced")
            if not indy_ok:
                ok = False
        except IndyRequestError as e:
            ok = False
    def db_check():
        try:
            User.objects.count()
            return True
        except django.db.Error:
            LOGGER.exception("Error during DB health check")
            return False
    ok = ok and await run_django(db_check)
    return web.Response(
        text='ok' if ok else '',
        status=200 if ok else 451)


async def status(request):
    """
    Return status of the Indy service including statistics on the requests performed
    """
    try:
        result = await _indy_client().get_status()
    except IndyRequestError as e:
        return e.response
    if INSTRUMENT:
        stats = STATS.copy()
        stats["avg"] = {task: stats["total"][task] / stats["count"][task] for task in stats["count"]}
        result["stats"] = stats
    return web.json_response(result)
