from asynctest import TestCase as AsyncTestCase

from .. import wallet_record as test_module
from ..wallet_record import WalletRecord


class TestIssuerCredRevRecord(AsyncTestCase):
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

        assert recs[0].requires_external_key
        assert not recs[1].requires_external_key

        rec_in_mem = WalletRecord(
            wallet_id="my-wallet-id-2",
            key_management_mode=WalletRecord.MODE_UNMANAGED,
            settings={
                "wallet.name": "my-wallet-2",
                "wallet.type": "in_memory",
                "wallet.key": "dummy-wallet-key-2",
            },
            wallet_name="my-wallet-2",
        )
        assert not rec_in_mem.requires_external_key
