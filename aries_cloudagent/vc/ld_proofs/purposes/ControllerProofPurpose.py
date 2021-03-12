from datetime import datetime, timedelta
from pyld import jsonld
from pyld.jsonld import JsonLdProcessor

from ..constants import SECURITY_CONTEXT_V2_URL
from ..suites import LinkedDataProof
from ..document_loader import DocumentLoader
from .ProofPurpose import ProofPurpose


class ControllerProofPurpose(ProofPurpose):
    def __init__(
        self, term: str, *, date: datetime = None, max_timestamp_delta: timedelta = None
    ):
        super().__init__(term=term, date=date, max_timestamp_delta=max_timestamp_delta)

    def validate(
        self,
        proof: dict,
        *,
        document: dict,
        suite: LinkedDataProof,
        verification_method: dict,
        document_loader: DocumentLoader,
    ) -> dict:
        try:
            result = super().validate(proof)

            if not result.get("valid"):
                raise result.get("error")

            verification_id = verification_method.get("id")
            controller = verification_method.get("controller")

            if isinstance(controller, dict):
                controller_id = controller.get("id")
            elif isinstance(controller, str):
                controller_id = controller
            else:
                raise Exception('"controller" must be a string or dict')

            framed = jsonld.frame(
                controller_id,
                {
                    "@context": SECURITY_CONTEXT_V2_URL,
                    "id": controller_id,
                    self.term: {"@embed": "@never", "id": verification_id},
                },
                {"documentLoader": document_loader},
            )

            result["controller"] = framed

            verification_methods = JsonLdProcessor.get_values(framed, self.term)
            result["valid"] = any(
                method == verification_id for method in verification_methods
            )

            if not result["valid"]:
                raise Exception(
                    f"Verification method {verification_id} not authorized by controller for proof purpose {self.term}"
                )

            return result

        except Exception as e:
            return {"valid": False, "error": e}
