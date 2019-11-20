import pytest
import os

from aries_cloudagent.wallet.indy import IndyWallet
from aries_cloudagent.storage.indy import IndyStorage
from aries_cloudagent.storage.record import StorageRecord
from aries_cloudagent.postgres import load_postgres_plugin

from . import test_basic_storage


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
class TestIndyStorage(test_basic_storage.TestBasicStorage):
    """ """

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

        load_postgres_plugin()
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
            value='{"initiator": "self", "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg", "state": "invitation", "routing_state": "none", "error_msg": null, "their_label": null, "created_at": "2019-05-14 21:58:24.143260+00:00", "updated_at": "2019-05-14 21:58:24.143260+00:00"}',
            tags={
                "initiator": "self",
                "invitation_key": "9XgL7Y4TBTJyVJdomT6axZGUFg9npxcrXnRT4CG8fWYg",
                "state": "invitation",
                "routing_state": "none",
            },
            type="connection",
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
