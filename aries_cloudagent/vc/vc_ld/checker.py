from pyld.jsonld import JsonLdProcessor
import re

from ...messaging.valid import RFC3339DateTime
from .constants import CREDENTIALS_CONTEXT_V1_URL


def get_id(obj):
    if type(obj) is str:
        return obj

    if "id" not in obj:
        return

    return obj["id"]


def check_credential(credential: dict):
    if not (
        credential["@context"]
        and credential["@context"][0] == CREDENTIALS_CONTEXT_V1_URL
    ):
        raise Exception(
            f"{CREDENTIALS_CONTEXT_V1_URL} needs to be first in the list of contexts"
        )

    if not credential["type"]:
        raise Exception('"type" property is required')

    if "VerifiableCredential" not in JsonLdProcessor.get_values(credential, "type"):
        raise Exception('"type" must include "VerifiableCredential"')

    if not credential["credentialSubject"]:
        raise Exception('"credentialSubject" property is required')

    if not credential["issuer"]:
        raise Exception('"issuer" property is required')

    if len(JsonLdProcessor.get_values(credential, "issuanceDate")) > 1:
        raise Exception('"issuanceDate" property can only have one value')

    if not credential["issuanceDate"]:
        raise Exception('"issuanceDate" property is required')

    if not re.match(RFC3339DateTime.PATTERN, credential["issuanceDate"]):
        raise Exception(
            f'"issuanceDate" must be a valid date {credential["issuanceDate"]}'
        )

    if len(JsonLdProcessor.get_values(credential, "issuer")) > 1:
        raise Exception('"issuer" property can only have one value')

    if "issuer" in credential:
        issuer = get_id(credential["issuer"])

        if not issuer:
            raise Exception('"issuer" id is required')

        if ":" not in issuer:
            raise Exception(f'"issuer" id must be a URL: {issuer}')

    if "credentialStatus" in credential:
        credential_status = credential["credentialStatus"]

        if not credential_status["id"]:
            raise Exception('"credentialStatus" must include an id')

        if not credential_status["type"]:
            raise Exception('"credentialStatus" must include a type')

    for evidence in JsonLdProcessor.get_values(credential, "evidence"):
        evidence_id = get_id(evidence)

        if evidence_id and ":" not in evidence_id:
            raise Exception(f'"evidence" id must be a URL: {evidence}')

    if "expirationDate" in credential and not re.match(
        RFC3339DateTime.PATTERN, credential["issuanceDate"]
    ):
        raise Exception(
            f'"expirationDate" must be a valid date {credential["expirationDate"]}'
        )
