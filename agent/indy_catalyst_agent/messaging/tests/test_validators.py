from ..validators import must_not_be_none

from marshmallow import ValidationError

from unittest import mock, TestCase


class TestAgentMessage(TestCase):
    """ """
    def test_data_is_blank(self):
        """ """
        try:
            must_not_be_none({})
        except:
            self.fail("must_not_be_none() raised Exception unexpectedly")

    def test_data_is_not_blank(self):
        """ """
        with self.assertRaises(ValidationError) as context:
            must_not_be_none(None)
        assert str(context.exception) == "Data not provided"
