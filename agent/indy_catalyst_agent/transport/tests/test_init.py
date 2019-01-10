from .. import Transport

from unittest import mock, TestCase


class TestTransport(TestCase):
    class BadImplementationClass(Transport):
        pass

    def test_init(self):
        with self.assertRaises(TypeError) as context:
            self.BadImplementationClass()  # pylint: disable=E0110

        assert (
            str(context.exception)
            == "Can't instantiate abstract class BadImplementationClass with abstract methods setup"
        )

