from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import help as command


class TestHelp(AsyncTestCase):
    def test_exec_help(self):
        with async_mock.patch.object(
            command.ArgumentParser, "print_help"
        ) as print_help:
            command.execute([])
            print_help.assert_called_once()
