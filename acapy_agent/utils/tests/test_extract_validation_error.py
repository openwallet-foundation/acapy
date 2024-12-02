import unittest

from aiohttp.web import HTTPUnprocessableEntity
from marshmallow.exceptions import ValidationError

from ...utils.extract_validation_error import extract_validation_error_message


class TestExtractValidationErrorMessage(unittest.TestCase):
    def test_validation_error_extracted(self):
        """Test that the validation error message is extracted when present."""
        validation_error = ValidationError({"field": ["Invalid input"]})
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")
        http_error.__cause__ = validation_error

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, {"field": ["Invalid input"]})

    def test_no_validation_error_returns_reason(self):
        """Test that the reason is returned when no ValidationError is found."""
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, "Unprocessable Entity")

    def test_deeply_nested_validation_error(self):
        """Test extraction when ValidationError is nested deeply."""
        validation_error = ValidationError({"field": ["Invalid input"]})
        level_3 = Exception("Level 3")
        level_3.__cause__ = validation_error
        level_2 = Exception("Level 2")
        level_2.__cause__ = level_3
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")
        http_error.__cause__ = level_2

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, {"field": ["Invalid input"]})

    def test_multiple_exceptions_no_validation_error(self):
        """Test that reason is returned when no ValidationError is in the chain."""
        level_2 = Exception("Level 2")
        level_1 = Exception("Level 1")
        level_1.__cause__ = level_2
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")
        http_error.__cause__ = level_1

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, "Unprocessable Entity")

    def test_validation_error_in_context(self):
        """Test extraction when ValidationError is in __context__ instead of __cause__."""
        validation_error = ValidationError({"field": ["Invalid input"]})
        level_1 = Exception("Level 1")
        level_1.__context__ = validation_error
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")
        http_error.__context__ = level_1

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, {"field": ["Invalid input"]})

    def test_exception_already_visited(self):
        """Test that visited set prevents infinite loops."""
        validation_error = ValidationError({"field": ["Invalid input"]})
        http_error = HTTPUnprocessableEntity(reason="Unprocessable Entity")
        # Create a loop in the exception chain
        validation_error.__cause__ = http_error
        http_error.__cause__ = validation_error

        result = extract_validation_error_message(http_error)
        self.assertEqual(result, {"field": ["Invalid input"]})

    def test_validation_error_as_initial_exception(self):
        """Test when the initial exception is a ValidationError."""
        validation_error = ValidationError({"field": ["Invalid input"]})

        result = extract_validation_error_message(validation_error)
        self.assertEqual(result, {"field": ["Invalid input"]})
