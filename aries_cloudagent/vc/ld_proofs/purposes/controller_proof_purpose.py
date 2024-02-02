"""Controller proof purpose class."""

from typing import TYPE_CHECKING

from pyld.jsonld import JsonLdProcessor
from pyld import jsonld

from ....resolver.default.web import WebDIDResolver

from ..constants import SECURITY_CONTEXT_URL, TRACEABILITY_CONTEXT_V1_URL
from ..document_loader import DocumentLoaderMethod
from ..error import LinkedDataProofException
from ..validation_result import PurposeResult

from .proof_purpose import ProofPurpose

# Avoid circular dependency
if TYPE_CHECKING:
    from ..suites import LinkedDataProof


class ControllerProofPurpose(ProofPurpose):
    """Controller proof purpose class."""

    def validate(
        self,
        *,
        proof: dict,
        document: dict,
        suite: "LinkedDataProof",
        verification_method: dict,
        document_loader: DocumentLoaderMethod,
    ) -> PurposeResult:
        """Validate whether verification method of proof is authorized by controller."""
        try:
            result = super().validate(
                proof=proof,
                document=document,
                suite=suite,
                verification_method=verification_method,
                document_loader=document_loader,
            )

            # Return early if super check was invalid
            if not result.valid:
                return result

            verification_id = verification_method.get("id")
            controller = verification_method.get("controller")

            if isinstance(controller, dict):
                controller_id = controller.get("id")
            elif isinstance(controller, str):
                controller_id = controller
            else:
                raise LinkedDataProofException('"controller" must be a string or dict')

            input_to_frame = controller_id
            # Get the controller
            # If the controller is a web did we first resolve the document
            if controller_id.startswith("did:web:"):
                did_document = WebDIDResolver()._resolve_with_request(controller_id)
                # We remove the traceability context if present
                # to avoid a bug with the pyld library
                # https://github.com/digitalbazaar/pyld/issues/188
                did_document["@context"] = [
                    i
                    for i in did_document["@context"]
                    if i != TRACEABILITY_CONTEXT_V1_URL
                ]
                input_to_frame = did_document

            # If we have the did_document accessible locally,
            # we use it as the input to frame
            # Otherwise we use the controller_id
            result.controller = jsonld.frame(
                input_to_frame,
                frame={
                    "@context": SECURITY_CONTEXT_URL,
                    "id": controller_id,
                    self.term: {"@embed": "@never", "id": verification_id},
                },
                options={
                    "documentLoader": document_loader,
                    "expandContext": SECURITY_CONTEXT_URL,
                    # if we don't set base explicitly it
                    # will remove the base in returned
                    # document (e.g. use key:z... instead of did:key:z...)
                    # same as compactToRelative in jsonld.js
                    "base": None,
                },
            )

            # Retrieve al verification methods on controller associated with term
            verification_methods = JsonLdProcessor.get_values(
                result.controller, self.term
            )

            # Check if any of the verification methods matches with the verification id
            result.valid = any(
                method == verification_id for method in verification_methods
            )

            if not result.valid:
                raise LinkedDataProofException(
                    f"Verification method {verification_id} not authorized"
                    f" by controller for proof purpose {self.term}"
                )

            return result

        except Exception as e:
            return PurposeResult(valid=False, error=str(e))
