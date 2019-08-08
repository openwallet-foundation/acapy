from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from .. import provision as command


class TestProvision(AsyncTestCase):
    def test_bad_calls(self):
        with self.assertRaises(command.ProvisionError):
            command.execute([])

        with self.assertRaises(SystemExit):
            command.execute(["bad"])

    @pytest.mark.indy
    def test_provision_wallet(self):
        test_seed = "testseed000000000000000000000001"
        command.execute(["--wallet-type", "indy", "--seed", test_seed])
