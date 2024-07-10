from unittest import TestCase

import pytest

from aries_cloudagent.vc.tests.data.test_ld_document_correct_schema import TEST_LD_DOCUMENT_CORRECT_SCHEMA
from aries_cloudagent.vc.vc_ld.models.credential import VerifiableCredential
from aries_cloudagent.vc.vc_ld.schema_validators.edtech_schema_validator import EdJsonVcSchemaValidator
from aries_cloudagent.vc.vc_ld.schema_validators.error import VcSchemaValidatorError
from aries_cloudagent.vc.vc_ld.schema_validators.validator_builder import validator_builder


class TestValidatorBuilder(TestCase):
    """Vc Schema Validator builder tests"""

    def test_unsupported_schema_validator(self):
        """Test unsupported type."""
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)

        with pytest.raises(VcSchemaValidatorError) as validator_error:
            validator_builder({"id": "https://example.com/schema.json", "type": "ExampleType"})

        assert validator_error.value.args[0] == "Unsupported credentialSchema type: ExampleType"

    def test_edtech_schema_validator(self):
        """Test 1EdTechJsonSchemaValidator2019 type."""
        vc = VerifiableCredential.deserialize(TEST_LD_DOCUMENT_CORRECT_SCHEMA)
        vc_schema_validator = validator_builder(vc.credential_schema[0])

        assert vc_schema_validator is issubclass(EdJsonVcSchemaValidator)
