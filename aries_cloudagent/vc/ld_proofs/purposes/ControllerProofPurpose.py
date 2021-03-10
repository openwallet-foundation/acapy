from datetime import datetime, timedelta

from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from ..constants import SECURITY_CONTEXT_V2_URL
from .ProofPurpose import ProofPurpose


class ControllerProofPurpose(ProofPurpose):
    def __init__(
        self, term: str, date: datetime = None, max_timestamp_delta: timedelta = None
    ):
        super().__init__(term, date, max_timestamp_delta)

    async def validate(
        self, proof: dict, verification_method: str, document_loader: callable
    ):
        try:
            result = await super(ProofPurpose, self).validate(proof)

            if not result["valid"]:
                raise result["error"]

            framed = jsonld.frame(
                verification_method,
                {
                    "@context": SECURITY_CONTEXT_V2_URL,
                    "@embed": "@always",
                    "id": verification_method,
                },
                {"documentLoader": document_loader},
            )

            result["controller"] = framed
            verification_id = verification_method["id"]

            verification_methods = JsonLdProcessor.get_values(
                result["controller"], self.term
            )
            result["valid"] = any(
                method == verification_id for method in verification_methods
            )

            if not result["valid"]:
                raise Exception(
                    f"Verification method {verification_method['id']} not authorized by controller for proof purpose {self.term}"
                )

            return result

        except Exception as e:
            return {"valid": False, "error": e}


__all__ = [ControllerProofPurpose]
