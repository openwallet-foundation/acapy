"""TODO."""


from .edtech_schema_validator import EdJsonVcSchemaValidator
from .schema_validator_base import VcSchemaValidator


def construct_validator(vc_schema:dict) -> VcSchemaValidator: 
    """TODO."""
    schema_type = vc_schema.get('type')
    if schema_type == '1EdTechJsonSchemaValidator2019':
        return EdJsonVcSchemaValidator(vc_schema)
    else:
        return VcSchemaValidator(vc_schema)
    