from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import help as command


class TestHelp(AsyncTestCase):
    def test_exec_help(self):
        command.execute([])
