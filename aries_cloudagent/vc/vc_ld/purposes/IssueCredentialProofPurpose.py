from datetime import datetime, timedelta
from pyld.jsonld import JsonLdProcessor

from ...ld_proofs.purposes import AssertionProofPurpose
from ...ld_proofs.suites import LinkedDataSignature


class IssueCredentialProofPurpose(AssertionProofPurpose):
    def __init__(self, date: datetime = None, max_timestamp_delta: timedelta = None):
        super().__init__(date, max_timestamp_delta)

    async def validate(
        self,
        proof: dict,
        document: dict,
        suite: LinkedDataSignature,
        verification_method: str,
        document_loader: callable,
    ):
        try:
            result = super().validate(proof, verification_method, document_loader)

            if not result["valid"]:
                raise result["error"]

            issuer = JsonLdProcessor.get_values(
                document, "https://www.w3.org/2018/credentials#issuer"
            )

            if not issuer or issuer.len() == 0:
                raise Exception("Credential issuer is required.")

            if result["controller"]["id"] != issuer[0]["id"]:
                raise Exception(
                    "Credential issuer must match the verification method controller."
                )

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "error": e}
