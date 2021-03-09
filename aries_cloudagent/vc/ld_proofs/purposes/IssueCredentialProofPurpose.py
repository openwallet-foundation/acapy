from .AssertionProofPurpose import AssertionProofPurpose
from datetime import datetime, timedelta
from ..suites import LinkedDataSignature
from pyld import jsonld


# TODO Move this file to the vc lib
class IssueCredentialProofPurpose(AssertionProofPurpose):
    def __init__(self, date: datetime, max_timestamp_delta: None):
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

            issuer = jsonld.get_values(
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


__all__ = [IssueCredentialProofPurpose]
