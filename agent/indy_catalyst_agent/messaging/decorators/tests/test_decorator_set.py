from ..base import DecoratorSet

from unittest import TestCase


class TestDecoratorSet(TestCase):
    def test_extract(self):

        decor_value = {}
        message = {"~decorator": decor_value, "one": "TWO"}

        decors = DecoratorSet()
        remain = decors.extract_decorators(message)

        # check unmodified
        assert "~decorator" in message

        assert decors["decorator"] is decor_value
        assert remain == {"one": "TWO"}

    def test_dict(self):

        decors = DecoratorSet()
        decors["test"] = "TEST"
        result = decors.to_dict()
        assert result == {"~test": "TEST"}
