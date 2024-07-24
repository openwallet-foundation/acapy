from unittest import IsolatedAsyncioTestCase

from aries_cloudagent.vc.vc_ld.validate import validate_presentation

from .test_credential import (
    PRESENTATION_SIGNED,
    PRESENTATION_INVALID_DATA_TYPE,
    PRESENTATION_VALID
)


class TestLDPresentationValidation(IsolatedAsyncioTestCase):

    async def test_validate_presentation_without_schema(self):
        validation_result = await validate_presentation(
            presentation=PRESENTATION_SIGNED,
        )

        assert validation_result.validated
        assert validation_result.errors == [] 

    async def test_validate_presentation_valid_credential(self):
        validation_result = await validate_presentation(
            presentation=PRESENTATION_VALID,
        )

        assert validation_result.validated
        assert validation_result.errors == [] 

    async def test_validate_presentation_invalid_credential(self):
        validation_result = await validate_presentation(
            presentation=PRESENTATION_INVALID_DATA_TYPE,
        )

        assert validation_result.validated is False
        assert len(validation_result.errors) > 0
