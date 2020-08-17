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

    async def test_provision_ledger_configured(self):
        with async_mock.patch.object(
            command, "wallet_config", async_mock.CoroutineMock()
        ) as mock_wallet_config, async_mock.patch.object(
            command, "ledger_config", async_mock.CoroutineMock(return_value=True)
        ) as mock_ledger_config:
            await command.provision({})

    def test_main(self):
        with async_mock.patch.object(
            command, "__name__", "__main__"
        ) as mock_name, async_mock.patch.object(
            command, "execute", async_mock.MagicMock()
        ) as mock_execute:
            command.main()
            mock_execute.assert_called_once
