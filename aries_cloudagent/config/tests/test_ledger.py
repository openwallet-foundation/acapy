from os import remove
from tempfile import NamedTemporaryFile

from asynctest import TestCase as AsyncTestCase, mock as async_mock

from ...ledger.base import BaseLedger
from ...ledger.error import LedgerError
from ...wallet.base import BaseWallet

from .. import ledger as test_module
from ..injection_context import InjectionContext

TEST_DID = "55GkHamhTU1ZbTbV2ab9DE"


class TestLedger(AsyncTestCase):
    async def test_fetch_genesis_transactions(self):
        with async_mock.patch.object(
            test_module, "fetch", async_mock.CoroutineMock()
        ) as mock_fetch:
            await test_module.fetch_genesis_transactions("http://1.2.3.4:9000/genesis")

    async def test_fetch_genesis_transactions_x(self):
        with async_mock.patch.object(
            test_module, "fetch", async_mock.CoroutineMock()
        ) as mock_fetch:
            mock_fetch.side_effect = test_module.FetchError("404 Not Found")
            with self.assertRaises(test_module.ConfigError):
                await test_module.fetch_genesis_transactions(
                    "http://1.2.3.4:9000/genesis"
                )

    async def test_ledger_config_genesis_url(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "default_endpoint": "http://1.2.3.4:8051",
            "profile_endpoint": "http://agent.ca",
        }
        mock_ledger = async_mock.MagicMock(
            get_txn_author_agreement=async_mock.CoroutineMock(
                return_value={
                    "taa_required": True,
                    "taa_record": {
                        "digest": b"ffffffffffffffffffffffffffffffffffffffff"
                    },
                }
            ),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(
                return_value={"digest": b"1234567890123456789012345678901234567890"}
            ),
            update_endpoint_for_did=async_mock.CoroutineMock(),
        )
        mock_wallet = async_mock.MagicMock(set_did_endpoint=async_mock.CoroutineMock())

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            mock_accept_taa.return_value = True
            await test_module.ledger_config(context, TEST_DID, provision=True)

    async def test_ledger_config_genesis_file(self):
        settings = {
            "ledger.genesis_file": "/tmp/genesis/path",
            "default_endpoint": "http://1.2.3.4:8051",
        }
        mock_ledger = async_mock.MagicMock(
            type="indy",
            get_txn_author_agreement=async_mock.CoroutineMock(
                return_value={
                    "taa_required": True,
                    "taa_record": {
                        "digest": b"ffffffffffffffffffffffffffffffffffffffff"
                    },
                }
            ),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(
                return_value={"digest": b"1234567890123456789012345678901234567890"}
            ),
        )
        mock_wallet = async_mock.MagicMock(
            type="indy", set_did_endpoint=async_mock.CoroutineMock()
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa, async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open:
            mock_open.return_value = async_mock.MagicMock(
                __enter__=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        read=async_mock.MagicMock(
                            return_value="... genesis transactions ..."
                        )
                    )
                )
            )
            mock_accept_taa.return_value = True
            await test_module.ledger_config(context, TEST_DID, provision=True)

    async def test_ledger_config_genesis_file_io_x(self):
        settings = {
            "ledger.genesis_file": "/tmp/genesis/path",
            "default_endpoint": "http://1.2.3.4:8051",
        }
        context = InjectionContext(settings=settings, enforce_typing=False)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open:
            mock_open.side_effect = IOError("no read permission")
            with self.assertRaises(test_module.ConfigError):
                await test_module.ledger_config(context, TEST_DID, provision=True)

    async def test_ledger_config_genesis_url_no_ledger(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "default_endpoint": "http://1.2.3.4:8051",
        }

        context = InjectionContext(settings=settings, enforce_typing=False)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            mock_accept_taa.return_value = True
            assert not await test_module.ledger_config(
                context, TEST_DID, provision=True
            )

    async def test_ledger_config_genesis_url_non_indy_ledger(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "default_endpoint": "http://1.2.3.4:8051",
        }
        mock_ledger = async_mock.MagicMock(
            type="fabric",
            get_txn_author_agreement=async_mock.CoroutineMock(
                return_value={
                    "taa_required": True,
                    "taa_record": {
                        "digest": b"ffffffffffffffffffffffffffffffffffffffff"
                    },
                }
            ),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(
                return_value={"digest": b"1234567890123456789012345678901234567890"}
            ),
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            mock_accept_taa.return_value = True
            assert not await test_module.ledger_config(
                context, TEST_DID, provision=True
            )

    async def test_ledger_config_genesis_url_no_taa_accept(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "default_endpoint": "http://1.2.3.4:8051",
        }
        mock_ledger = async_mock.MagicMock(
            type="indy",
            get_txn_author_agreement=async_mock.CoroutineMock(
                return_value={
                    "taa_required": True,
                    "taa_record": {
                        "digest": b"ffffffffffffffffffffffffffffffffffffffff"
                    },
                }
            ),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(
                return_value={"digest": b"1234567890123456789012345678901234567890"}
            ),
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            mock_accept_taa.return_value = False
            assert not await test_module.ledger_config(
                context, TEST_DID, provision=True
            )

    async def test_ledger_config_read_only_skip_taa_accept(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "read_only_ledger": True,
        }
        mock_ledger = async_mock.MagicMock(
            type="indy",
            get_txn_author_agreement=async_mock.CoroutineMock(),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(),
        )
        mock_wallet = async_mock.MagicMock(
            type="indy",
            set_did_endpoint=async_mock.CoroutineMock(
                side_effect=LedgerError(
                    "Error cannot update endpoint when ledger is in read only mode"
                )
            ),
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            with self.assertRaises(test_module.ConfigError) as x_context:
                await test_module.ledger_config(context, TEST_DID, provision=True)
            assert "ledger is in read only mode" in str(x_context.exception)
            mock_ledger.get_txn_author_agreement.assert_not_called()
            mock_ledger.get_latest_txn_author_acceptance.assert_not_called()

    async def test_ledger_config_read_only_skip_profile_endpoint_publish(self):
        settings = {
            "ledger.genesis_url": "00000000000000000000000000000000",
            "read_only_ledger": True,
            "profile_endpoint": "http://agent.ca",
        }
        mock_ledger = async_mock.MagicMock(
            type="indy",
            get_txn_author_agreement=async_mock.CoroutineMock(),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(),
        )
        mock_wallet = async_mock.MagicMock(
            type="indy",
            set_did_endpoint=async_mock.CoroutineMock(),
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "fetch_genesis_transactions", async_mock.CoroutineMock()
        ) as mock_fetch, async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa:
            await test_module.ledger_config(context, TEST_DID, provision=True)
            mock_ledger.get_txn_author_agreement.assert_not_called()
            mock_ledger.get_latest_txn_author_acceptance.assert_not_called()
            mock_ledger.update_endpoint_for_did.assert_not_called()

    async def test_ledger_config_genesis_file_non_indy_wallet(self):
        settings = {
            "ledger.genesis_file": "/tmp/genesis/path",
            "default_endpoint": "http://1.2.3.4:8051",
        }
        mock_ledger = async_mock.MagicMock(
            type="indy",
            get_txn_author_agreement=async_mock.CoroutineMock(
                return_value={
                    "taa_required": True,
                    "taa_record": {
                        "digest": b"ffffffffffffffffffffffffffffffffffffffff"
                    },
                }
            ),
            get_latest_txn_author_acceptance=async_mock.CoroutineMock(
                return_value={"digest": b"1234567890123456789012345678901234567890"}
            ),
        )
        mock_wallet = async_mock.MagicMock(
            type="trifold", set_did_endpoint=async_mock.CoroutineMock()
        )

        context = InjectionContext(settings=settings, enforce_typing=False)
        context.injector.bind_instance(BaseLedger, mock_ledger)
        context.injector.bind_instance(BaseWallet, mock_wallet)

        with async_mock.patch.object(
            test_module, "accept_taa", async_mock.CoroutineMock()
        ) as mock_accept_taa, async_mock.patch(
            "builtins.open", async_mock.MagicMock()
        ) as mock_open:
            mock_open.return_value = async_mock.MagicMock(
                __enter__=async_mock.MagicMock(
                    return_value=async_mock.MagicMock(
                        read=async_mock.MagicMock(
                            return_value="... genesis transactions ..."
                        )
                    )
                )
            )
            mock_accept_taa.return_value = True
            with self.assertRaises(test_module.ConfigError):
                await test_module.ledger_config(context, TEST_DID, provision=True)

    @async_mock.patch("sys.stdout")
    async def test_ledger_accept_taa_not_tty(self, mock_stdout):
        mock_stdout.isatty = async_mock.MagicMock(return_value=False)

        assert not await test_module.accept_taa(None, None, provision=False)

    @async_mock.patch("sys.stdout")
    async def test_ledger_accept_taa(self, mock_stdout):
        mock_stdout.isatty = async_mock.MagicMock(return_value=True)

        taa_info = {
            "taa_record": {"version": "1.0", "text": "Agreement"},
            "aml_record": {"aml": ["wallet_agreement", "on_file"]},
        }

        with async_mock.patch.object(
            test_module, "use_asyncio_event_loop", async_mock.MagicMock()
        ) as mock_use_aio_loop, async_mock.patch.object(
            test_module.prompt_toolkit, "prompt", async_mock.CoroutineMock()
        ) as mock_prompt:
            mock_prompt.side_effect = EOFError()
            assert not await test_module.accept_taa(None, taa_info, provision=False)

        with async_mock.patch.object(
            test_module, "use_asyncio_event_loop", async_mock.MagicMock()
        ) as mock_use_aio_loop, async_mock.patch.object(
            test_module.prompt_toolkit, "prompt", async_mock.CoroutineMock()
        ) as mock_prompt:
            mock_prompt.return_value = "x"
            assert not await test_module.accept_taa(None, taa_info, provision=False)

        with async_mock.patch.object(
            test_module, "use_asyncio_event_loop", async_mock.MagicMock()
        ) as mock_use_aio_loop, async_mock.patch.object(
            test_module.prompt_toolkit, "prompt", async_mock.CoroutineMock()
        ) as mock_prompt:
            mock_ledger = async_mock.MagicMock(
                accept_txn_author_agreement=async_mock.CoroutineMock()
            )
            mock_prompt.return_value = ""
            assert await test_module.accept_taa(mock_ledger, taa_info, provision=False)
