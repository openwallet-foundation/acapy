"""1EdTechJsonSchemaValidator2019 credentialSchema validator."""

from typing import Dict, List
from jsonschema import Draft201909Validator, ValidationError
from aries_cloudagent.vc.ld_proofs.schema_validators.error import VcSchemaValidatorError
from .schema_validator_base import VcSchemaValidator
from aries_cloudagent.vc.vc_ld.models.credential import VerifiableCredential
import json

class EdJsonVcSchemaValidator(VcSchemaValidator):
    """Class implementation for 1EdTechJsonSchemaValidator2019 type."""
    def __init__(self, vc_schema: Dict):
        """Initializes the EdJsonVcSchemaValidator."""
        super().__init__(vc_schema)

    @property
    def schema_id(self):
        """Getter for schema id."""
        return self._schema_id

    @schema_id.setter
    def schema_id(self, id):
        """Checks the id follows 1EdTechJsonSchemaValidator2019 type requirements."""
        if isinstance(id, str) and type is not None:
            if id.startswith("https"):
                self._schema_id = id
            else: 
                raise VcSchemaValidatorError(
                f'The HTTP scheme MUST be "https" for {id}'
                )
        else: 
            raise VcSchemaValidatorError(
                "id must be a string."
                )
    
    def validate(self, vc: VerifiableCredential):
        """Validates a given VerifiableCredential against its credentialSchema.

        :param vc: the Verifiable Credential to validate
        :raises VcSchemaValidatorError: errors for invalid VC.
        :return: True if valid
        """

        validation_errors = []
        schema_json = self.fetch(self.schema_id)
        validator = Draft201909Validator(schema_json, 
                                         format_checker=Draft201909Validator.FORMAT_CHECKER)
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
        
        error_details = []

        def traverse_errors(errors):
            for error in errors:
                if error.context is not None:
                    traverse_errors(error.context)

                details = {
                    "reason": str(error.message),
                    "json_path": error.json_path,
                    "schema_path": [str(item) for item in error.schema_path]
                }
                error_details.append(details)

        traverse_errors(errors)

        error = {
            "message": "Credential does not conform to Schema",
            "details": error_details
        }
        return json.dumps(error)