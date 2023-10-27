import pytest

from aries_cloudagent.tests import mock
from unittest import IsolatedAsyncioTestCase

from ...config.base import ConfigError
from ...config.error import ArgsParseError
from .. import provision as test_module
from ...protocols.coordinate_mediation.mediation_invite_store import (
    MediationInviteRecord,
)


class TestProvision(IsolatedAsyncioTestCase):
    def test_bad_calls(self):
        with self.assertRaises(ArgsParseError):
            test_module.execute([])

        with self.assertRaises(SystemExit):
            test_module.execute(["bad"])

    @pytest.mark.indy
    def test_provision_wallet(self):
        test_seed = "testseed000000000000000000000001"
        test_module.execute(
            [
                "--wallet-type",
                "indy",
                "--wallet-name",
                "test_wallet",
                "--wallet-key",
                "key",
                "--seed",
                test_seed,
                "--no-ledger",
                "--endpoint",
                "test_endpoint",
                "--recreate-wallet",
            ]
        )

    async def test_provision_ledger_configured(self):
        profile = mock.MagicMock(close=mock.CoroutineMock())
        with mock.patch.object(
            test_module,
            "wallet_config",
            mock.CoroutineMock(
                return_value=(
                    profile,
                    mock.CoroutineMock(did="public DID", verkey="verkey"),
                )
            ),
        ) as mock_wallet_config, mock.patch.object(
            test_module, "ledger_config", mock.CoroutineMock(return_value=True)
        ) as mock_ledger_config:
            await test_module.provision({})

    async def test_provision_config_x(self):
        with mock.patch.object(
            test_module, "wallet_config", mock.CoroutineMock()
        ) as mock_wallet_config:
            mock_wallet_config.side_effect = ConfigError("oops")
            with self.assertRaises(test_module.ProvisionError):
                await test_module.provision({})

    def test_main(self):
        with mock.patch.object(
            test_module, "__name__", "__main__"
        ) as mock_name, mock.patch.object(
            test_module, "execute", mock.MagicMock()
        ) as mock_execute:
            test_module.main()
            mock_execute.assert_called_once

    async def test_provision_should_store_provided_mediation_invite(self):
        # given
        mediation_invite = "test-invite"

        with mock.patch.object(
            test_module.MediationInviteStore, "store"
        ) as invite_store:
            # when
            await test_module.provision({"mediation.invite": mediation_invite})

            # then
            invite_store.assert_called_with(
                MediationInviteRecord(mediation_invite, False)
            )
