from datetime import datetime, timedelta
from pyld.jsonld import JsonLdProcessor
from pyld import jsonld

from ..constants import SECURITY_V2_URL
from ..suites import LinkedDataProof
from ..document_loader import DocumentLoader
from .ProofPurpose import ProofPurpose


class ControllerProofPurpose(ProofPurpose):
    def __init__(
        self, term: str, date: datetime = None, max_timestamp_delta: timedelta = None
    ):
        super().__init__(term=term, date=date, max_timestamp_delta=max_timestamp_delta)

    def validate(
        self,
        proof: dict,
        document: dict,
        suite: LinkedDataProof,
        verification_method: dict,
        document_loader: DocumentLoader,
    ) -> dict:
        try:
            result = super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )

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
                frame={
                    "@context": SECURITY_V2_URL,
                    "id": controller_id,
                    self.term: {"@embed": "@never", "id": verification_id},
                },
                options={
                    "documentLoader": document_loader,
                    "expandContext": SECURITY_V2_URL,
                    # if we don't set base explicitly it will remove the base in returned
                    # document (e.g. use key:z... instead of did:key:z...)
                    # same as compactToRelative in jsonld.js
                    "base": None,
                },
            )

            result["controller"] = framed

            verification_methods = JsonLdProcessor.get_values(
                result.get("controller"), self.term
            )
            result["valid"] = any(
                method == verification_id for method in verification_methods
            )

            if not result.get("valid"):
                raise Exception(
                    f"Verification method {verification_id} not authorized by controller for proof purpose {self.term}"
                )

            return result

        except Exception as e:
            return {"valid": False, "error": e}
