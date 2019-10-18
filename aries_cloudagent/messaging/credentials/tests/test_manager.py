from asyncio import sleep

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .. import manager as test_module

from ....storage.error import StorageNotFoundError


class TestCredentialManager(AsyncTestCase):
    def setUp(self):
        self.mock_context = async_mock.MagicMock()
        self.test_instance = test_module.CredentialManager(self.mock_context)

    # async def test_store_credential_calls_remove_expired_records(self):
    #     mock_credential_offer_message = async_mock.MagicMock()

    #     with async_mock.patch.object(
    #         test_module, "CredentialExchange", autospec=True
    #     ) as mock_credential_exchange, async_mock.patch.object(
    #         test_module, "json", autospec=True
    #     ) as mock_json:
    #         mock_json.loads.return_value = async_mock.MagicMock()

    #         mock_credential_exchange_instance = (
    #             mock_credential_exchange.return_value
    #         ) = async_mock.CoroutineMock()

    #         mock_credential_exchange_instance.save = async_mock.CoroutineMock()

    #         mock_ledger = async_mock.CoroutineMock()
    #         mock_ledger.get_credential_definition = async_mock.CoroutineMock()
    #         mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

    #         mock_holder = async_mock.CoroutineMock()
    #         mock_holder.store_credential = async_mock.CoroutineMock()
    #         mock_holder.get_credential = async_mock.CoroutineMock()

    #         inject = self.test_instance.context.inject = async_mock.CoroutineMock()
    #         inject.side_effect = [mock_ledger, mock_holder]

    #         self.test_instance.remove_expired_records = async_mock.CoroutineMock()

    #         await self.test_instance.store_credential(
    #             mock_credential_exchange_instance, ""
    #         )

    #         self.test_instance.remove_expired_records.assert_called_once_with(
    #             mock_credential_exchange_instance,
    #             mock_credential_exchange.INITIATOR_EXTERNAL,
    #             "credential_exchange::offer_exchange_id::",
    #         )

    # async def test_credential_stored_calls_remove_expired_records(self):
    #     mock_credential_offer_message = async_mock.MagicMock()

    #     with async_mock.patch.object(
    #         test_module, "CredentialExchange", autospec=True
    #     ) as mock_credential_exchange, async_mock.patch.object(
    #         test_module, "json", autospec=True
    #     ) as mock_json:
    #         mock_json.loads.return_value = async_mock.MagicMock()

    #         mock_credential_exchange_instance = (
    #             mock_credential_exchange.retrieve_by_tag_filter.return_value
    #         ) = async_mock.CoroutineMock()

    #         mock_credential_exchange_instance.save = async_mock.CoroutineMock()

    #         mock_ledger = async_mock.CoroutineMock()
    #         mock_ledger.get_credential_definition = async_mock.CoroutineMock()
    #         mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

    #         mock_holder = async_mock.CoroutineMock()
    #         mock_holder.store_credential = async_mock.CoroutineMock()
    #         mock_holder.get_credential = async_mock.CoroutineMock()

    #         inject = self.test_instance.context.inject = async_mock.CoroutineMock()
    #         inject.side_effect = [mock_ledger, mock_holder]

    #         self.test_instance.remove_expired_records = async_mock.CoroutineMock()

    #         await self.test_instance.credential_stored(
    #             async_mock.CoroutineMock()
    #         )

    #         self.test_instance.remove_expired_records.assert_called_once_with(
    #             mock_credential_exchange_instance,
    #             mock_credential_exchange.INITIATOR_SELF,
    #             "credential_exchange::",
    #         )

    async def test_credential_stored_no_parent_not_deleted(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.retrieve_by_tag_filter.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            inject.side_effect = [mock_ledger, mock_holder]

            mock_credential_exchange_instance.parent_thread_id = None
            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            mock_credential_stored_message = async_mock.CoroutineMock()

            await self.test_instance.credential_stored(mock_credential_stored_message)

            assert not mock_credential_exchange_instance.delete_record.called


    async def test_credential_stored_parent_so_deleted(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.retrieve_by_tag_filter.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            inject.side_effect = [mock_ledger, mock_holder]

            mock_credential_exchange_instance.parent_thread_id = "thread id"
            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            mock_credential_stored_message = async_mock.CoroutineMock()

            await self.test_instance.credential_stored(mock_credential_stored_message)

            assert mock_credential_exchange_instance.delete_record.called



    async def test_credential_stored_parent_but_cached_so_not_deleted(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.retrieve_by_tag_filter.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            inject.side_effect = [mock_ledger, mock_holder]

            mock_credential_exchange_instance.parent_thread_id = "thread id"
            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            mock_credential_stored_message = async_mock.CoroutineMock()

            # Old cred query
            old_credential_exchange = async_mock.CoroutineMock()

            mock_credential_exchange.query = async_mock.CoroutineMock()
            mock_credential_exchange.query.side_effect = [[old_credential_exchange]]

            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            # cache value comes out same as current exchange id
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.get = async_mock.CoroutineMock()
            mock_cache.get.return_value = old_credential_exchange.credential_exchange_id

            await self.test_instance.credential_stored(mock_credential_stored_message)

            assert not old_credential_exchange.delete_record.called









    async def test_remove_expired_records_with_parent_deleted(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:

            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            inject.side_effect = [mock_ledger, mock_holder]

            mock_credential_exchange_instance.parent_thread_id = True
            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            await self.test_instance.remove_expired_records(
                mock_credential_exchange.return_value, "", ""
            )

            mock_credential_exchange_instance.delete_record.assert_called_once()

    async def test_remove_expired_records_old_record_in_cache_not_delete(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            old_credential_exchange = async_mock.CoroutineMock()

            mock_credential_exchange.query = async_mock.CoroutineMock()
            mock_credential_exchange.query.side_effect = [[old_credential_exchange]]

            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            # cache value comes out same as current exchange id
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.get = async_mock.CoroutineMock()
            mock_cache.get.return_value = old_credential_exchange.credential_exchange_id

            await self.test_instance.remove_expired_records(
                mock_credential_exchange.return_value, "", ""
            )

            assert not old_credential_exchange.delete_record.called

    async def test_remove_expired_records_old_record_has_children_not_delete(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            old_credential_exchange = async_mock.CoroutineMock()
            child_credential_exchange = async_mock.CoroutineMock()

            mock_credential_exchange.query = async_mock.CoroutineMock()
            mock_credential_exchange.query.side_effect = [
                [old_credential_exchange],
                [child_credential_exchange],
            ]

            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            # cache value comes out same as current exchange id
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.get = async_mock.CoroutineMock()
            mock_cache.get.return_value = "no same"

            await self.test_instance.remove_expired_records(
                mock_credential_exchange.return_value, "", ""
            )

            assert not old_credential_exchange.delete_record.called

    async def test_remove_expired_records_old_record_no_children_deleted(self):
        mock_credential_offer_message = async_mock.MagicMock()

        with async_mock.patch.object(
            test_module, "CredentialExchange", autospec=True
        ) as mock_credential_exchange, async_mock.patch.object(
            test_module, "json", autospec=True
        ) as mock_json:
            mock_json.loads.return_value = async_mock.MagicMock()

            mock_credential_exchange_instance = (
                mock_credential_exchange.return_value
            ) = async_mock.CoroutineMock()

            mock_credential_exchange_instance.save = async_mock.CoroutineMock()

            mock_ledger = async_mock.CoroutineMock()
            mock_ledger.get_credential_definition = async_mock.CoroutineMock()
            mock_ledger.__aexit__ = mock_ledger.__aenter__ = async_mock.CoroutineMock()

            mock_holder = async_mock.CoroutineMock()
            mock_holder.store_credential = async_mock.CoroutineMock()
            mock_holder.get_credential = async_mock.CoroutineMock()

            old_credential_exchange = async_mock.CoroutineMock()
            old_credential_exchange.delete_record = async_mock.CoroutineMock()

            mock_credential_exchange.query = async_mock.CoroutineMock()
            mock_credential_exchange.query.side_effect = [[old_credential_exchange], []]

            mock_credential_exchange_instance.delete_record = async_mock.CoroutineMock()

            # cache value comes out same as current exchange id
            inject = self.test_instance.context.inject = async_mock.CoroutineMock()
            mock_cache = inject.return_value
            mock_cache.get = async_mock.CoroutineMock()
            mock_cache.get.return_value = "no same"

            await self.test_instance.remove_expired_records(
                mock_credential_exchange.return_value, "", ""
            )

            old_credential_exchange.delete_record.assert_called_once()
