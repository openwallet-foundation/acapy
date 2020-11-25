import asyncio
import json
import pytest
import os

import indy.anoncreds
import indy.crypto
import indy.did
import indy.wallet

from asynctest import mock as async_mock

from aries_cloudagent.wallet import indy as test_wallet
from aries_cloudagent.wallet.indy import IndyWallet
from aries_cloudagent.storage.error import StorageError, StorageSearchError
from aries_cloudagent.storage.indy import IndyStorage
from aries_cloudagent.storage.record import StorageRecord

from .. import indy as test_module
from . import test_in_memory_storage


@pytest.fixture()
async def store():
    key = await IndyWallet.generate_wallet_key()
    wallet = IndyWallet(
        {
            "auto_create": True,
            "auto_remove": True,
            "name": "test-wallet",
            "key": key,
            "key_derivation_method": "RAW",  # much slower tests with argon-hashed keys
        }
    )
    await wallet.open()
    yield IndyStorage(wallet)
    await wallet.close()


@pytest.mark.indy
class TestIndyStorage(test_in_memory_storage.TestInMemoryStorage):
    """Tests for indy storage."""

    @pytest.mark.asyncio
    async def test_record(self):
        with async_mock.patch.object(
            test_wallet, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            fake_wallet = IndyWallet(
                {
                    "auto_create": True,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": await IndyWallet.generate_wallet_key(),
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": json.dumps({"url": "dummy"}),
                    "storage_creds": json.dumps(
                        {
                            "account": "postgres",
                            "password": "mysecretpassword",
                            "admin_account": "postgres",
                            "admin_password": "mysecretpassword",
                        }
                    ),
                }
            )
            await fake_wallet.open()
            storage = IndyStorage(fake_wallet)

            for record_x in [
                None,
                StorageRecord(
                    type="connection",
                    value=json.dumps(
                        {
                            "initiator": "self",
                            "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                            "state": "invitation",
                            "routing_state": "none",
                            "error_msg": None,
                            "their_label": None,
                            "created_at": "2019-05-14 21:58:24.143260+00:00",
                            "updated_at": "2019-05-14 21:58:24.143260+00:00",
                        }
                    ),
                    tags={
                        "initiator": "self",
                        "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                        "state": "invitation",
                        "routing_state": "none",
                    },
                    id=None,
                ),
                StorageRecord(
                    type=None,
                    value=json.dumps(
                        {
                            "initiator": "self",
                            "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                            "state": "invitation",
                            "routing_state": "none",
                            "error_msg": None,
                            "their_label": None,
                            "created_at": "2019-05-14 21:58:24.143260+00:00",
                            "updated_at": "2019-05-14 21:58:24.143260+00:00",
                        }
                    ),
                    tags={
                        "initiator": "self",
                        "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                        "state": "invitation",
                        "routing_state": "none",
                    },
                    id="f96f76ec-0e9b-4f32-8237-f4219e6cf0c7",
                ),
                StorageRecord(
                    type="connection",
                    value=None,
                    tags={
                        "initiator": "self",
                        "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                        "state": "invitation",
                        "routing_state": "none",
                    },
                    id="f96f76ec-0e9b-4f32-8237-f4219e6cf0c7",
                ),
            ]:
                with pytest.raises(StorageError):
                    await storage.add_record(record_x)

            with pytest.raises(StorageError):
                await storage.get_record(None, "dummy-id")
            with pytest.raises(StorageError):
                await storage.get_record("connection", None)

            with async_mock.patch.object(
                test_module.non_secrets, "get_wallet_record", async_mock.CoroutineMock()
            ) as mock_get_record:
                mock_get_record.side_effect = test_module.IndyError(
                    test_module.ErrorCode.CommonInvalidStructure
                )
                with pytest.raises(test_module.StorageError):
                    await storage.get_record("connection", "dummy-id")

            with async_mock.patch.object(
                test_module.non_secrets,
                "update_wallet_record_value",
                async_mock.CoroutineMock(),
            ) as mock_update_value, async_mock.patch.object(
                test_module.non_secrets,
                "update_wallet_record_tags",
                async_mock.CoroutineMock(),
            ) as mock_update_tags, async_mock.patch.object(
                test_module.non_secrets,
                "delete_wallet_record",
                async_mock.CoroutineMock(),
            ) as mock_delete:
                mock_update_value.side_effect = test_module.IndyError(
                    test_module.ErrorCode.CommonInvalidStructure
                )
                mock_update_tags.side_effect = test_module.IndyError(
                    test_module.ErrorCode.CommonInvalidStructure
                )
                mock_delete.side_effect = test_module.IndyError(
                    test_module.ErrorCode.CommonInvalidStructure
                )

                rec = StorageRecord(
                    type="connection",
                    value=json.dumps(
                        {
                            "initiator": "self",
                            "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                            "state": "invitation",
                            "routing_state": "none",
                            "error_msg": None,
                            "their_label": None,
                            "created_at": "2019-05-14 21:58:24.143260+00:00",
                            "updated_at": "2019-05-14 21:58:24.143260+00:00",
                        }
                    ),
                    tags={
                        "initiator": "self",
                        "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                        "state": "invitation",
                        "routing_state": "none",
                    },
                    id="f96f76ec-0e9b-4f32-8237-f4219e6cf0c7",
                )

                with pytest.raises(test_module.StorageError):
                    await storage.update_record(rec, "dummy-value", {"tag": "tag"})

                with pytest.raises(test_module.StorageError):
                    await storage.delete_record(rec)

    @pytest.mark.asyncio
    async def test_storage_search_x(self):
        with async_mock.patch.object(
            test_wallet, "load_postgres_plugin", async_mock.MagicMock()
        ) as mock_load, async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            fake_wallet = IndyWallet(
                {
                    "auto_create": True,
                    "auto_remove": True,
                    "name": "test_pg_wallet",
                    "key": await IndyWallet.generate_wallet_key(),
                    "key_derivation_method": "RAW",
                    "storage_type": "postgres_storage",
                    "storage_config": json.dumps({"url": "dummy"}),
                    "storage_creds": json.dumps(
                        {
                            "account": "postgres",
                            "password": "mysecretpassword",
                            "admin_account": "postgres",
                            "admin_password": "mysecretpassword",
                        }
                    ),
                }
            )
            await fake_wallet.open()
            storage = IndyStorage(fake_wallet)

            search = storage.search_records("connection")
            with pytest.raises(StorageSearchError):
                await search.fetch(10)

            with async_mock.patch.object(
                indy.non_secrets, "open_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_open_search, async_mock.patch.object(
                indy.non_secrets, "close_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_close_search:
                mock_indy_open_search.side_effect = test_module.IndyError("no open")
                search = storage.search_records("connection")
                with pytest.raises(StorageSearchError):
                    await search.fetch()
                await search.close()

            with async_mock.patch.object(
                indy.non_secrets, "open_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_open_search, async_mock.patch.object(
                indy.non_secrets,
                "fetch_wallet_search_next_records",
                async_mock.CoroutineMock(),
            ) as mock_indy_fetch, async_mock.patch.object(
                indy.non_secrets, "close_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_close_search:
                mock_indy_fetch.side_effect = test_module.IndyError("no fetch")
                search = storage.search_records("connection")
                with pytest.raises(StorageSearchError):
                    await search.fetch(10)
                await search.close()

            with async_mock.patch.object(
                indy.non_secrets, "open_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_open_search, async_mock.patch.object(
                indy.non_secrets, "close_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_close_search:
                mock_indy_close_search.side_effect = test_module.IndyError("no close")
                search = storage.search_records("connection")
                with pytest.raises(StorageSearchError):
                    await search.fetch_all()

    @pytest.mark.asyncio
    async def test_storage_del_close(self):
        with async_mock.patch.object(
            indy.wallet, "create_wallet", async_mock.CoroutineMock()
        ) as mock_create, async_mock.patch.object(
            indy.wallet, "open_wallet", async_mock.CoroutineMock()
        ) as mock_open, async_mock.patch.object(
            indy.anoncreds, "prover_create_master_secret", async_mock.CoroutineMock()
        ) as mock_master, async_mock.patch.object(
            indy.wallet, "close_wallet", async_mock.CoroutineMock()
        ) as mock_close, async_mock.patch.object(
            indy.wallet, "delete_wallet", async_mock.CoroutineMock()
        ) as mock_delete:
            fake_wallet = IndyWallet(
                {
                    "auto_create": True,
                    "auto_remove": True,
                    "name": "test_indy_wallet",
                    "key": await IndyWallet.generate_wallet_key(),
                    "key_derivation_method": "RAW",
                }
            )
            await fake_wallet.open()
            storage = IndyStorage(fake_wallet)

            with async_mock.patch.object(
                indy.non_secrets, "open_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_open_search, async_mock.patch.object(
                indy.non_secrets, "close_wallet_search", async_mock.CoroutineMock()
            ) as mock_indy_close_search:
                mock_indy_open_search.return_value = 1
                search = storage.search_records("connection")
                mock_indy_open_search.assert_not_awaited()
                await search._open()
                mock_indy_open_search.assert_awaited_once()
                del search
                c = 0
                # give the pending cleanup task time to be scheduled
                while not mock_indy_close_search.await_count and c < 10:
                    await asyncio.sleep(0.1)
                    c += 1
                mock_indy_close_search.assert_awaited_once_with(1)

    # TODO get these to run in docker ci/cd
    @pytest.mark.asyncio
    @pytest.mark.postgres
    async def test_postgres_wallet_storage_works(self):
        """
        Ensure that postgres wallet operations work (create and open wallet, store and search, drop wallet)
        """
        postgres_url = os.environ.get("POSTGRES_URL")
        if not postgres_url:
            pytest.fail("POSTGRES_URL not configured")

        wallet_key = await IndyWallet.generate_wallet_key()
        postgres_wallet = IndyWallet(
            {
                "auto_create": False,
                "auto_remove": False,
                "name": "test_pg_wallet",
                "key": wallet_key,
                "key_derivation_method": "RAW",
                "storage_type": "postgres_storage",
                "storage_config": '{"url":"' + postgres_url + '", "max_connections":5}',
                "storage_creds": '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}',
            }
        )
        await postgres_wallet.create()
        await postgres_wallet.open()

        storage = IndyStorage(postgres_wallet)

        # add and then fetch a record
        record = StorageRecord(
            type="connection",
            value=json.dumps(
                {
                    "initiator": "self",
                    "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                    "state": "invitation",
                    "routing_state": "none",
                    "error_msg": None,
                    "their_label": None,
                    "created_at": "2019-05-14 21:58:24.143260+00:00",
                    "updated_at": "2019-05-14 21:58:24.143260+00:00",
                }
            ),
            tags={
                "initiator": "self",
                "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                "state": "invitation",
                "routing_state": "none",
            },
            id="f96f76ec-0e9b-4f32-8237-f4219e6cf0c7",
        )
        await storage.add_record(record)
        g_rec = await storage.get_record(record.type, record.id)

        # now try search
        search = None
        try:
            search = storage.search_records("connection")
            await search.open()
            records = await search.fetch(10)
        finally:
            if search:
                await search.close()

        await postgres_wallet.close()
        await postgres_wallet.remove()
