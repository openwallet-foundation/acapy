from asynctest import mock as async_mock, TestCase as AsyncTestCase

from ...config.injection_context import InjectionContext

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
            assert text == "tails-hash"

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
