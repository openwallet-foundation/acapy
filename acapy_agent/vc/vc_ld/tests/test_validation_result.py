from unittest import TestCase

from ..validation_result import PresentationVerificationResult


class TestValidationResult(TestCase):
    def test_properties(self):
        result = PresentationVerificationResult(verified=True)
        result2 = PresentationVerificationResult(verified=True)

        assert result.__repr__()
        assert result == result2
        assert result != 10
