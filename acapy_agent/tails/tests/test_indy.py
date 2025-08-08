from unittest import IsolatedAsyncioTestCase

from ...config.injection_context import InjectionContext
from ...ledger.base import BaseLedger
from ...ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager
from ...tests import mock
from ...utils.testing import create_test_profile
from .. import indy_tails_server as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"


class TestIndyTailsServer(IsolatedAsyncioTestCase):
    async def test_upload_no_tails_upload_url_x(self):
        context = InjectionContext(settings={"ledger.genesis_transactions": "dummy"})
        indy_tails = test_module.IndyTailsServer()

        with self.assertRaises(test_module.TailsServerNotConfiguredError):
            await indy_tails.upload_tails_file(context, REV_REG_ID, "/tmp/dummy/path")

    async def test_upload(self):
        context = InjectionContext(
            settings={
                "ledger.genesis_transactions": "dummy",
                "tails_server_base_url": "http://1.2.3.4:8088/tails/",
                "tails_server_upload_url": "http://1.2.3.4:8088",
            }
        )
        indy_tails = test_module.IndyTailsServer()

        with mock.patch.object(test_module, "put_file", mock.CoroutineMock()) as mock_put:
            mock_put.return_value = "tails-hash"
            (ok, text) = await indy_tails.upload_tails_file(
                context,
                REV_REG_ID,
                "/tmp/dummy/path",
            )
            assert ok

            # already contains / from config, no need to add it
            assert text == context.settings["tails_server_base_url"] + REV_REG_ID
            assert (
                mock_put.call_args.args[0]
                == context.settings["tails_server_upload_url"] + "/" + REV_REG_ID
            )

    async def test_upload_indy_vdr(self):
        self.profile = await create_test_profile()
        self.profile.settings["tails_server_base_url"] = "http://1.2.3.4:8088/tails/"
        self.profile.settings["tails_server_upload_url"] = "http://1.2.3.4:8088"
        mock_multi_ledger_manager = mock.MagicMock(
            BaseMultipleLedgerManager, autospec=True
        )
        mock_multi_ledger_manager.get_write_ledgers = mock.CoroutineMock(
            return_value=[
                "test_ledger_id_1",
                "test_ledger_id_2",
            ]
        )
        self.profile.context.injector.bind_instance(
            BaseMultipleLedgerManager, mock_multi_ledger_manager
        )
        mock_ledger = mock.MagicMock(BaseLedger, autospec=True)
        mock_ledger.pool = mock.MagicMock(
            genesis_txns="dummy genesis transactions",
        )
        self.profile.context.injector.bind_instance(BaseLedger, mock_ledger)
        indy_tails = test_module.IndyTailsServer()

        with mock.patch.object(test_module, "put_file", mock.CoroutineMock()) as mock_put:
            mock_put.return_value = "tails-hash"
            (ok, text) = await indy_tails.upload_tails_file(
                self.profile.context,
                REV_REG_ID,
                "/tmp/dummy/path",
            )
            assert ok

            # already contains / from config, no need to add it
            assert text == self.profile.settings["tails_server_base_url"] + REV_REG_ID
            assert (
                mock_put.call_args.args[0]
                == self.profile.settings["tails_server_upload_url"] + "/" + REV_REG_ID
            )

    async def test_upload_x(self):
        context = InjectionContext(
            settings={
                "ledger.genesis_transactions": "dummy",
                "tails_server_base_url": "http://1.2.3.4:8088/tails/",
                "tails_server_upload_url": "http://1.2.3.4:8088",
            }
        )
        indy_tails = test_module.IndyTailsServer()

        with mock.patch.object(test_module, "put_file", mock.CoroutineMock()) as mock_put:
            mock_put.side_effect = test_module.PutError("Server down for maintenance")

            (ok, text) = await indy_tails.upload_tails_file(
                context, REV_REG_ID, "/tmp/dummy/path"
            )
            assert not ok
            assert text == "Server down for maintenance"
