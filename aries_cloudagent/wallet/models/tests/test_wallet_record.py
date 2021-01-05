from asynctest import TestCase as AsyncTestCase

from ..wallet_record import WalletRecord


class TestWalletRecord(AsyncTestCase):
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
