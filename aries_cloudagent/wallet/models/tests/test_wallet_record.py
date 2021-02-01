from asynctest import TestCase as AsyncTestCase

from ..wallet_record import WalletRecord
from ...error import WalletSettingsError


class TestWalletRecord(AsyncTestCase):
    async def test_serde(self):
        rec = WalletRecord(
            wallet_id="my-wallet-id",
            key_management_mode=WalletRecord.MODE_MANAGED,
            settings={
                "wallet.name": "my-wallet",
                "wallet.type": "indy",
                "wallet.key": "dummy-wallet-key",
            },
            wallet_name="my-wallet",
        )
        ser = rec.serialize()
        assert ser["wallet_id"] == rec.wallet_id
        assert ser["key_management_mode"] == WalletRecord.MODE_MANAGED
        assert len(ser["settings"]) == 4

        assert rec == WalletRecord.deserialize(ser)

    async def test_rec_ops(self):
        recs = [
            WalletRecord(
                wallet_id=f"my-wallet-id-{i}",
                key_management_mode=[
                    WalletRecord.MODE_UNMANAGED,
                    WalletRecord.MODE_MANAGED,
                ][i],
                settings={
                    "wallet.name": f"my-wallet-{i}",
                    "wallet.type": "indy",
                    "wallet.key": f"dummy-wallet-key-{i}",
                },
                wallet_name=f"my-wallet-{i}",
            )
            for i in range(2)
        ]
        assert recs[0].wallet_id
        assert recs[0] != recs[1]
        assert recs[0].wallet_name
        assert recs[0].wallet_type == "indy"
        assert recs[0].wallet_key
        assert recs[0].record_value

        assert not recs[0].is_managed
        assert recs[1].is_managed

    async def test_requires_external_key_in_memory(self):
        wallet_record = WalletRecord(
            settings={"wallet.type": "in_memory"},
        )

        # should be false for in_memory wallets
        assert wallet_record.requires_external_key is False

    async def test_requires_external_key_managed(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            settings={"wallet.type": "indy"},
            key_management_mode=WalletRecord.MODE_MANAGED,
        )

        # should be false for managed wallets
        assert wallet_record.requires_external_key is False

    async def test_requires_external_key_unmanaged(self):
        wallet_record = WalletRecord(
            wallet_id="test",
            settings={"wallet.type": "indy"},
            key_management_mode=WalletRecord.MODE_UNMANAGED,
        )

        # should return true if wallet is unmanaged and wallet_type != unmanaged
        assert wallet_record.requires_external_key is True

    async def test_update_settings(self):
        wallet_record = WalletRecord(
            settings={"wallet.type": "in_memory"},
        )
        settings = {
            "wallet.type": "indy",
        }
        wallet_record.update_settings(settings)

        assert wallet_record.settings.get("wallet.type") == "indy"

    async def test_update_settings(self):
        wallet_record = WalletRecord()
        settings = {
            "wallet.id": "my-wallet-id",
        }
        with self.assertRaises(WalletSettingsError):
            wallet_record.update_settings(settings)
