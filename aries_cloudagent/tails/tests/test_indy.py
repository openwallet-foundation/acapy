from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext
from ...core.in_memory import InMemoryProfile
from ...ledger.base import BaseLedger
from ...ledger.multiple_ledger.base_manager import BaseMultipleLedgerManager

from .. import indy_tails_server as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"


class TestIndyTailsServer(AsyncTestCase):
    async def test_upload_no_tails_upload_url_x(self):
        context = InjectionContext(settings={"ledger.genesis_transactions": "dummy"})
        indy_tails = test_module.IndyTailsServer()

        with self.assertRaises(test_module.TailsServerNotConfiguredError):
            await indy_tails.upload_tails_file(context, REV_REG_ID, "/tmp/dummy/path")

    async def test_upload(self):
        context = InjectionContext(
            settings={
                "ledger.genesis_transactions": "dummy",
                "tails_server_upload_url": "http://1.2.3.4:8088",
            }
        )
        indy_tails = test_module.IndyTailsServer()

        with async_mock.patch.object(
            test_module, "put_file", async_mock.CoroutineMock()
        ) as mock_put:
            mock_put.return_value = "tails-hash"
            (ok, text) = await indy_tails.upload_tails_file(
                context,
                REV_REG_ID,
                "/tmp/dummy/path",
            )
            assert ok
            assert (
                text == context.settings["tails_server_upload_url"] + "/" + REV_REG_ID
            )

    async def test_upload_indy_sdk(self):
        profile = InMemoryProfile.test_profile()
        profile.settings["tails_server_upload_url"] = "http://1.2.3.4:8088"
        profile.context.injector.bind_instance(
            BaseMultipleLedgerManager,
            async_mock.MagicMock(
                get_write_ledgers=async_mock.CoroutineMock(
                    return_value=[
                        "test_ledger_id_1",
                        "test_ledger_id_2",
                    ]
                )
            ),
        )
        profile.context.injector.bind_instance(BaseLedger, async_mock.MagicMock())
        indy_tails = test_module.IndyTailsServer()

        with async_mock.patch.object(
            test_module, "put_file", async_mock.CoroutineMock()
        ) as mock_put:
            mock_put.return_value = "tails-hash"
            (ok, text) = await indy_tails.upload_tails_file(
                profile.context,
                REV_REG_ID,
                "/tmp/dummy/path",
            )
            assert ok
            assert (
                text == profile.settings["tails_server_upload_url"] + "/" + REV_REG_ID
            )

    async def test_upload_indy_vdr(self):
        profile = InMemoryProfile.test_profile()
        profile.settings["tails_server_upload_url"] = "http://1.2.3.4:8088"
        profile.context.injector.bind_instance(
            BaseMultipleLedgerManager,
            async_mock.MagicMock(
                get_write_ledgers=async_mock.CoroutineMock(
                    return_value=[
                        "test_ledger_id_1",
                        "test_ledger_id_2",
                    ]
                )
            ),
        )
        profile.context.injector.bind_instance(BaseLedger, async_mock.MagicMock())
        indy_tails = test_module.IndyTailsServer()

        with async_mock.patch.object(
            test_module, "put_file", async_mock.CoroutineMock()
        ) as mock_put:
            mock_put.return_value = "tails-hash"
            (ok, text) = await indy_tails.upload_tails_file(
                profile.context,
                REV_REG_ID,
                "/tmp/dummy/path",
            )
            assert ok
            assert (
                text == profile.settings["tails_server_upload_url"] + "/" + REV_REG_ID
            )

    async def test_upload_x(self):
        context = InjectionContext(
            settings={
                "ledger.genesis_transactions": "dummy",
                "tails_server_upload_url": "http://1.2.3.4:8088",
            }
        )
        indy_tails = test_module.IndyTailsServer()

        with async_mock.patch.object(
            test_module, "put_file", async_mock.CoroutineMock()
        ) as mock_put:
            mock_put.side_effect = test_module.PutError("Server down for maintenance")

            (ok, text) = await indy_tails.upload_tails_file(
                context, REV_REG_ID, "/tmp/dummy/path"
            )
            assert not ok
            assert text == "Server down for maintenance"
