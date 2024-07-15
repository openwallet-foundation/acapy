"""Verifiable Credential and Presentation validation methods."""

import asyncio
from typing import Union
from pyld.jsonld import JsonLdProcessor

from aries_cloudagent.vc.vc_ld.models.credential import VerifiableCredential
from .schema_validators.error import VcSchemaValidatorError
from .schema_validators.validator_builder import validator_builder
from .schema_validation_result import ValidationResult

async def _validate_credential(
    *,
    credential: Union[dict, VerifiableCredential],
) -> ValidationResult:
    """Validate credential against credentialSchema if present."""

    if isinstance(credential, VerifiableCredential):
        vc = credential
    else:
        vc = VerifiableCredential.deserialize(credential)

    errors = []
    credential_schemas = vc.credential_schema
    if isinstance(credential_schemas, dict):
        credential_schemas = [credential_schemas]
    
    if credential_schemas:
        for credential_schema in credential_schemas:
            try:
                validator = validator_builder(credential_schema)
                validator.validate(vc)
            except VcSchemaValidatorError as e:
                errors.append(e)

    validated = len(errors) == 0

    return ValidationResult(validated=validated, errors=errors)


async def validate_credential(
    *,
    credential: Union[dict, VerifiableCredential],
) -> ValidationResult:
    """Validate credential against its credentialSchema.
    
    Args:
        credential (dict): The credential to validate
    Returns:
        ValidationResult: The result of the validation. Validated property
            indicates whether the validation was successful

    """
    try:
        return await _validate_credential(
            credential=credential,
        )
    except Exception as e:
        return ValidationResult(
            validated=False, errors=[e]
        )


async def _validate_presentation(
    *,
    presentation: dict,
):
    """Validate presentation credentials."""
    
    credentials = JsonLdProcessor.get_values(presentation, "verifiableCredential")
    credential_results = await asyncio.gather(
        *[
            validate_credential(
                credential=credential,
            )
            for credential in credentials
        ]
    )

    credentials_validated = all(result.validated for result in credential_results)
    credential_errors = [result.errors for result in credential_results if result.errors]

    return ValidationResult(
        validated=credentials_validated,
        errors=credential_errors,
    )


async def validate_presentation(
    *,
    presentation: dict,
) -> ValidationResult:
    """Validate credentials in a presentation.

    Args:
        presentation (dict): The presentation to validate

    Returns:
        ValidationResult: The result of the validation. validated property
            indicates whether the validation was successful

    """

    try:
        return await _validate_presentation(
            presentation=presentation,
        )
    except Exception as e:
        return ValidationResult(validated=False, errors=[e])


__all__ = ["validate_presentation"]
