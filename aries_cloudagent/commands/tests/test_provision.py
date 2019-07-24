from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import provision as command


class TestProvision(AsyncTestCase):
    def test_bad_category(self):
        with async_mock.patch.object(
            command.ArgumentParser, "print_usage"
        ) as print_usage:
            with self.assertRaises(SystemExit):
                command.execute([])
            print_usage.assert_called_once()

        with self.assertRaises(SystemExit):
            command.execute(["bad"])

    def test_provision_wallet(self):
        test_seed = "testseed000000000000000000000001"
        command.execute(["wallet", "--seed", test_seed])
