"""1EdTechJsonSchemaValidator2019 credentialSchema validator."""

from typing import List
from jsonschema import Draft201909Validator, ValidationError
import jsonschema

from aries_cloudagent.vc.ld_proofs.schema_validators.error import VcSchemaValidatorError
from .schema_validator_base import VcSchemaValidator
from aries_cloudagent.vc.vc_ld.models.credential import VerifiableCredential
import json

class EdJsonVcSchemaValidator(VcSchemaValidator):
    """Class implementation for 1EdTechJsonSchemaValidator2019 type."""
    def __init__(self, vc_schema: dict):
        """Initializes the EdJsonVcSchemaValidator."""
        self._schema_type = self.check_type(vc_schema.get('type'))
        self._schema_id = self.check_id(vc_schema.get('id'))

    def check_id(self,id) -> str:
        """Checks the id follows 1EdTechJsonSchemaValidator2019 type requirements."""
        if isinstance(id, str) or id is None:
            if id.startswith("https"):
                return id
            else: 
                raise VcSchemaValidatorError(
                f'The HTTP scheme MUST be "https" for {id}'
                )
        else: 
            raise VcSchemaValidatorError(
                "credentialSchema id must be a string."
                )
    
    def validate(self, vc: VerifiableCredential):
        """Validates a given VerifiableCredential against its credentialSchema.

        :param vc: the Verifiable Credential to validate
        :raises VcSchemaValidatorError: errors for invalid VC.
        :return: True if valid
        """

        validation_errors = []
        schema_json = self.download(self.schema_id, {"TLS_1_3": True})
        validator = Draft201909Validator(schema_json, format_checker=Draft201909Validator.FORMAT_CHECKER)
        validator.check_schema(schema_json)


        vc_json = json.loads(vc.to_json())
        validation_errors.extend(validator.iter_errors(vc_json))

        if len(validation_errors) > 0:
            formatted  = self.format_validation_errors(validation_errors)
            raise VcSchemaValidatorError(formatted)

        return True
    
    def format_validation_errors(self, errors:List[ValidationError]):
        """Formats a list of errors from validating the VC.

        :param errors: the errors to format
        """

        by_relevance = sorted(errors, key=jsonschema.exceptions.relevance)

        error_details = []

        def traverse_errors(errors):
            for error in errors:
                if error.context is not None:
                    traverse_errors(error.context)

                details = {
                    "reason": str(error.message),
                    "credential_path": str('$.' + '.'.join([str(item) for item in error.relative_path])),
                    "schema_path": [str(item) for item in error.relative_schema_path]
                }
                error_details.append(details)

        traverse_errors(by_relevance)
        # TODO: Standardize?
        prefix = "Credential does not conform to Schema"

        error = {
            "message": prefix,
            "details": error_details
        }
        return json.dumps(error)