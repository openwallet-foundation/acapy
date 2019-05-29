import logging

from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework import permissions

from rest_framework.response import Response
from django.http import JsonResponse
from django.http import Http404

from api_indy.indy.issuer import IssuerManager, IssuerException
from api_indy.indy.credential_offer import CredentialOfferManager
from api_indy.indy.credential import Credential, CredentialManager
from api_indy.indy.proof_request import ProofRequest
from api_indy.indy.proof import ProofManager

from api_indy.decorators.jsonschema import validate
from api_indy.jsonschema.issuer import ISSUER_JSON_SCHEMA
from api_indy.jsonschema.credential_offer import CREDENTIAL_OFFER_JSON_SCHEMA
from api_indy.jsonschema.credential import CREDENTIAL_JSON_SCHEMA
from api_indy.jsonschema.construct_proof import CONSTRUCT_PROOF_JSON_SCHEMA

from api_indy.tob_anchor.boot import indy_client, indy_holder_id

from vonx.common.eventloop import run_coro
from vonx.indy.messages import (
    ProofRequest as VonxProofRequest,
    ConstructedProof as VonxConstructedProof,
)

logger = logging.getLogger(__name__)


@api_view(["POST"])
#@permission_classes((IsSignedRequest,))
@validate(CREDENTIAL_OFFER_JSON_SCHEMA)
def generate_credential_request(request, *args, **kwargs):
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

    logger.warn(">>> Generate credential request")

    credential_offer = request.data["credential_offer"]
    credential_definition_id = request.data["credential_definition_id"]
    credential_offer_manager = CredentialOfferManager(
        credential_offer, credential_definition_id
    )

    credential_request, credential_request_metadata = (
        credential_offer_manager.generate_credential_request()
    )

    result = {
        "credential_request": credential_request,
        "credential_request_metadata": credential_request_metadata,
    }

    logger.warn("<<< Generate credential request")
    return JsonResponse({"success": True, "result": result})


@api_view(["POST"])
#@permission_classes((IsSignedRequest,))
@validate(CREDENTIAL_JSON_SCHEMA)
def store_credential(request, *args, **kwargs):
    """
    Stores a verifiable credential in wallet.

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

    returns: created verified credential model
    """
    logger.warn(">>> Store Credential")

    return store_credential_int(request.data)


def store_credential_int(request_data):
    print(">>> Store Credential Internal")

    credential_data = request_data["credential_data"]
    credential_request_metadata = request_data["credential_request_metadata"]

    logger.info(credential_data)

    credential = Credential(credential_data, wallet_id=credential_data["referent"])
    credential_manager = CredentialManager()

    credential_wallet_id = credential_manager.process(credential)

    return Response({"success": True, "result": credential_data["referent"]})


@api_view(["POST"])
#@permission_classes((IsSignedRequest,))
@validate(ISSUER_JSON_SCHEMA)
# TODO: Clean up abstraction. IssuerManager writes only –
#       use serializer in view to return created models?
def register_issuer(request, *args, **kwargs):
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

    logger.warn(">>> Register issuer")
    try:
        issuer_manager = IssuerManager()
        updated = issuer_manager.register_issuer(request, request.data)
        response = {"success": True, "result": updated}
    except IssuerException as e:
        logger.exception("Issuer request not accepted:")
        response = {"success": False, "result": str(e)}
    logger.warn("<<< Register issuer")
    return JsonResponse(response)


@api_view(["POST"])
#@permission_classes((IsSignedRequest,))
@validate(CONSTRUCT_PROOF_JSON_SCHEMA)
def construct_proof(request, *args, **kwargs):
    """
    Constructs a proof given a proof request

    ```json
    {
        "proof_request": <HL Indy proof request>
    }
    ```

    returns: HL Indy proof data
    """
    logger.warn(">>> Construct Proof")

    proof_request = request.data.get("proof_request")
    cred_ids = request.data.get("credential_ids")

    if isinstance(cred_ids, str):
        cred_ids = (c.strip() for c in 'a, b'.split(','))
    if isinstance(cred_ids, list):
        cred_ids = set(filter(None, cred_ids))
    else:
        cred_ids = None

    proof_manager = ProofManager(proof_request, cred_ids)
    proof = proof_manager.construct_proof()

    return JsonResponse({"success": True, "result": proof})


@api_view(["GET"])
#@permission_classes((IsSignedRequest,))
def verify_credential(request, *args, **kwargs):
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
    logger.warn(">>> Verify Credential")
    credential_id = kwargs.get("id")

    if not credential_id:
        raise Http404

    try:
        credential = CredentialModel.objects.get(id=credential_id)
    except CredentialModel.DoesNotExist as error:
        logger.warn(error)
        raise Http404

    proof_request = ProofRequest(name="the-org-book", version="1.0.0")
    proof_request.build_from_credential(credential)

    proof_manager = ProofManager(proof_request.dict, {credential.wallet_id})
    proof = proof_manager.construct_proof()

    async def verify():
        return await indy_client().verify_proof(
            indy_holder_id(),
            VonxProofRequest(proof_request.dict),
            VonxConstructedProof(proof))
    verified = run_coro(verify())

    verified = verified.verified

    return JsonResponse(
        {
            "success": verified,
            "result": {
                "verified": verified,
                "proof": proof,
                "proof_request": proof_request.dict,
            },
        }
    )

@api_view(["GET"])
def status(request, *args, **kwargs):
    async def get_status():
        return await indy_client().get_status()
    return JsonResponse(run_coro(get_status()))
