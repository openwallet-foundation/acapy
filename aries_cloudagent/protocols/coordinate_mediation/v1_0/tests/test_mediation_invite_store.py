from asynctest import TestCase as AsyncTestCase
from unittest import TestCase
from asynctest import mock as async_mock

from aries_cloudagent.protocols.coordinate_mediation.mediation_invite_store import (
    MediationInviteStore,
    MediationInviteRecord,
    NoDefaultMediationInviteException,
)
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.storage.record import StorageRecord


def _storage_record_for(value: str, used: bool = False) -> StorageRecord:
    return StorageRecord(
        type=MediationInviteStore.INVITE_RECORD_CATEGORY,
        value=f"""{{"invite": "{value}", "used": {str(used).lower()}}}""",
        tags={},
        id=MediationInviteStore.MEDIATION_INVITE_ID,
    )


class TestMediationInviteRecord(TestCase):
    def test_to_json_should_dump_record(self):
        # given
        invite_record = MediationInviteRecord("some_invite", True)

        # when
        json_record = invite_record.to_json()

        # then
        assert json_record == """{"invite": "some_invite", "used": true}"""

    def test_from_json_should_create_record_from_json(self):
        # given
        json_record = """{"invite": "some_invite", "used": true}"""

        # when
        record = MediationInviteRecord.from_json(json_record)

        # then
        assert record == MediationInviteRecord("some_invite", True)

    def test_unused_should_create_unused_record(self):
        # when - then
        assert not MediationInviteRecord.unused("some_other_invite").used


class TestMediationInviteStore(AsyncTestCase):
    def setUp(self):
        self.storage = async_mock.MagicMock(spec=BaseStorage)
        self.mediation_invite_store = MediationInviteStore(self.storage)

    async def test_store_create_record_to_store_mediation_invite_when_no_record_exists(
        self,
    ):
        # given
        mediation_invite_url = "somepla.ce:4242/alongandunreadablebase64payload"
        self.storage.get_record.side_effect = StorageNotFoundError

        expected_updated_record = MediationInviteRecord.unused(mediation_invite_url)

        # when
        stored_invite = await self.mediation_invite_store.store(
            MediationInviteRecord.unused(mediation_invite_url)
        )

        # then
        self.storage.add_record.assert_called_with(
            _storage_record_for(mediation_invite_url)
        )
        assert stored_invite == expected_updated_record

    async def test_store_should_update_record_when_a_mediation_invite_record_exists(
        self,
    ):
        # given
        stored_record = _storage_record_for("some old url")
        mediation_invite_url = "somepla.ce:4242/alongandunreadablebase64payload"
        self.storage.get_record.return_value = stored_record

        expected_updated_record = MediationInviteRecord.unused(mediation_invite_url)

        # when
        stored_invite = await self.mediation_invite_store.store(
            MediationInviteRecord.unused(mediation_invite_url)
        )

        # then
        self.storage.update_record.assert_called_with(
            stored_record, expected_updated_record.to_json(), tags=stored_record.tags
        )

        assert stored_invite == expected_updated_record

    async def test_mark_default_invite_as_used_should_mark_stored_invite(self):
        # given
        stored_record = _storage_record_for("some old url")
        self.storage.get_record.return_value = stored_record

        # when
        updated_invite_record = (
            await self.mediation_invite_store.mark_default_invite_as_used()
        )

        # then
        assert updated_invite_record.used

    async def test_mark_default_invite_as_used_should_raise_when_no_invite(self):
        # given
        self.storage.get_record.return_value = None

        # when - then
        with self.assertRaises(NoDefaultMediationInviteException):
            await self.mediation_invite_store.mark_default_invite_as_used()

    async def test_get_mediation_invite_record_returns_none_when_no_invite_available(
        self,
    ):
        # given
        self.storage.get_record.side_effect = StorageNotFoundError

        # when
        invite = await self.mediation_invite_store.get_mediation_invite_record(None)

        # then
        assert invite is None

    async def test_get_mediation_invite_returns_stored_record_when_no_invite_provided(
        self,
    ):
        # given
        stored_record = _storage_record_for(
            "somepla.ce:4242/alongandunreadablebase64payload"
        )
        expected_invite = MediationInviteRecord.from_json(stored_record.value)
        self.storage.get_record.return_value = stored_record

        # when
        invite = await self.mediation_invite_store.get_mediation_invite_record(None)

        # then
        assert invite == expected_invite

    async def test_get_mediation_invite_stores_and_returns_provided_invite_if_none_stored(
        self,
    ):
        # given
        expected_invite = MediationInviteRecord.unused(
            "somepla.ce:4242/alongandunreadablebase64payload"
        )
        self.storage.get_record.return_value = None

        # when
        invite = await self.mediation_invite_store.get_mediation_invite_record(
            expected_invite.invite
        )

        # then
        assert invite == expected_invite
