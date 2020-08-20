from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from ...config.injection_context import InjectionContext

from .. import indy_tails_server as test_module

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"
CRED_DEF_ID = f"{TEST_DID}:3:CL:1234:default"
REV_REG_ID = f"{TEST_DID}:4:{CRED_DEF_ID}:CL_ACCUM:0"


class TestIndyTailsServer(AsyncTestCase):
    async def test_upload_no_tails_base_url_x(self):
        context = InjectionContext(settings={"ledger.genesis_transactions": "dummy"})
        indy_tails = test_module.IndyTailsServer()

        with self.assertRaises(test_module.TailsServerNotConfiguredError):
            await indy_tails.upload_tails_file(context, REV_REG_ID, "/tmp/dummy/path")

    async def test_upload(self):
        context = InjectionContext(
            settings={
                "ledger.genesis_transactions": "dummy",
                "tails_server_base_url": "http://1.2.3.4:8088",
            }
        )
        indy_tails = test_module.IndyTailsServer()

        with async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open, async_mock.patch.object(
            test_module.aiohttp, "ClientSession", async_mock.MagicMock()
        ) as mock_cli_session:
            mock_open.return_value = async_mock.MagicMock(
                __enter__=async_mock.MagicMock()
            )
            mock_cli_session.return_value = async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        put=async_mock.MagicMock(
                            return_value=async_mock.MagicMock(
                                __aenter__=async_mock.CoroutineMock(
                                    return_value=async_mock.MagicMock(status=200)
                                )
                            )
                        )
                    )
                )
            )
            (ok, reason) = await indy_tails.upload_tails_file(
                context, REV_REG_ID, "/tmp/dummy/path"
            )
            assert ok
            assert reason is None

        with async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open, async_mock.patch.object(
            test_module.aiohttp, "ClientSession", async_mock.MagicMock()
        ) as mock_cli_session:
            mock_open.return_value = async_mock.MagicMock(
                __enter__=async_mock.MagicMock()
            )
            mock_cli_session.return_value = async_mock.MagicMock(
                __aenter__=async_mock.CoroutineMock(
                    return_value=async_mock.MagicMock(
                        put=async_mock.MagicMock(
                            return_value=async_mock.MagicMock(
                                __aenter__=async_mock.CoroutineMock(
                                    return_value=async_mock.MagicMock(
                                        status=403, reason="Unauthorized"
                                    )
                                )
                            )
                        )
                    )
                )
            )
            (ok, reason) = await indy_tails.upload_tails_file(
                context, REV_REG_ID, "/tmp/dummy/path"
            )
            assert not ok
            assert reason == "Unauthorized"
