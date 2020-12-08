from asynctest import TestCase as AsyncTestCase

from ....core.in_memory import InMemoryProfile
from ....protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
)
from ....protocols.connections.v1_0.messages.connection_request import ConnectionRequest
from ....protocols.connections.v1_0.models.connection_detail import ConnectionDetail
from ....storage.base import BaseStorage
from ....storage.error import StorageNotFoundError

from ..conn_record import ConnRecord
from ..diddoc.diddoc import DIDDoc


class TestConnRecord(AsyncTestCase):
    def setUp(self):
        self.session = InMemoryProfile.test_session()

        self.test_seed = "testseed000000000000000000000001"
        self.test_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.test_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        self.test_endpoint = "http://localhost"

        self.test_target_did = "GbuDUYXaUZRfHD2jeDuQuP"
        self.test_target_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"

        self.test_conn_record = ConnRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=ConnRecord.Role.REQUESTER.rfc23,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        assert self.test_conn_record.their_role == ConnRecord.Role.REQUESTER.rfc160
        assert self.test_conn_record.state == ConnRecord.State.COMPLETED.rfc160

    async def test_get_enums(self):
        assert ConnRecord.Role.get("Larry") is None
        assert ConnRecord.State.get("a suffusion of yellow") is None

        assert (
            ConnRecord.Role.get(ConnRecord.Role.REQUESTER) is ConnRecord.Role.REQUESTER
        )

        assert (
            ConnRecord.State.get(ConnRecord.State.RESPONSE) is ConnRecord.State.RESPONSE
        )

        assert ConnRecord.Role.REQUESTER.flip() is ConnRecord.Role.RESPONDER
        assert ConnRecord.Role.get(
            ConnRecord.Role.REQUESTER.rfc160
        ) is ConnRecord.Role.get(ConnRecord.Role.REQUESTER.rfc23)
        assert ConnRecord.Role.REQUESTER == ConnRecord.Role.REQUESTER.rfc160  # check ==
        assert ConnRecord.Role.REQUESTER == ConnRecord.Role.REQUESTER.rfc23
        assert ConnRecord.Role.REQUESTER != ConnRecord.Role.RESPONDER.rfc23

    async def test_save_retrieve_compare(self):
        record = ConnRecord(my_did=self.test_did)
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)
        assert fetched and fetched == record

        bad_record = ConnRecord(my_did=None)
        bad_record._id = record._id
        bad_record.created_at = record.created_at
        bad_record.updated_at = record.updated_at
        assert bad_record != record

        record = ConnRecord(
            state=ConnRecord.State.INIT,  # exercise init State by enum
            my_did=self.test_did,
            their_role=ConnRecord.Role.REQUESTER,  # exercise init Role by enum
        )
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)
        assert fetched and fetched == record
        assert fetched.state is ConnRecord.State.INIT.rfc160
        assert ConnRecord.State.get(fetched.state) is ConnRecord.State.INIT
        assert fetched.their_role is ConnRecord.Role.REQUESTER.rfc160
        assert ConnRecord.Role.get(fetched.their_role) is ConnRecord.Role.REQUESTER

        record160 = ConnRecord(
            state=ConnRecord.State.INIT.rfc23,
            my_did=self.test_did,
            their_role=ConnRecord.Role.REQUESTER.rfc23,
        )
        record160._id = record._id
        record160.created_at = record.created_at
        record160.updated_at = record.updated_at
        assert record160 == record

    async def test_retrieve_by_did(self):
        record = ConnRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.COMPLETED.rfc23,
        )
        rec_id = await record.save(self.session)
        result = await ConnRecord.retrieve_by_did(
            session=self.session,
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc160,
        )
        assert result == record

    async def test_retrieve_by_invitation_key(self):
        record = ConnRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc160,
            state=ConnRecord.State.INVITATION.rfc23,
            invitation_key="dummy",
        )
        await record.save(self.session)
        result = await ConnRecord.retrieve_by_invitation_key(
            session=self.session,
            invitation_key="dummy",
            their_role=ConnRecord.Role.RESPONDER.rfc23,
        )
        assert result == record
        with self.assertRaises(StorageNotFoundError):
            await ConnRecord.retrieve_by_invitation_key(
                session=self.session,
                invitation_key="dummy",
                their_role=ConnRecord.Role.REQUESTER.rfc23,
            )

    async def test_retrieve_by_request_id(self):
        record = ConnRecord(
            my_did=self.test_did,
            their_did=self.test_target_did,
            their_role=ConnRecord.Role.RESPONDER.rfc23,
            state=ConnRecord.State.COMPLETED.rfc23,
            request_id="abc123",
        )
        await record.save(self.session)
        result = await ConnRecord.retrieve_by_request_id(
            session=self.session, request_id="abc123"
        )
        assert result == record

    async def test_completed_is_ready(self):
        record = ConnRecord(my_did=self.test_did, state=ConnRecord.State.COMPLETED)
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)

        assert fetched.is_ready == True

    async def test_response_is_ready(self):
        record = ConnRecord(my_did=self.test_did, state=ConnRecord.State.RESPONSE)
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)

        assert fetched.is_ready is True

    async def test_request_is_not_ready(self):
        record = ConnRecord(my_did=self.test_did, state=ConnRecord.State.REQUEST)
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)

        assert fetched.is_ready is False

    async def test_invitation_is_not_multi_use(self):
        record = ConnRecord(
            my_did=self.test_did,
            state=ConnRecord.State.INVITATION.rfc23,
            invitation_mode=ConnRecord.INVITATION_MODE_ONCE,
        )
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)

        assert fetched.is_multiuse_invitation is False

    async def test_invitation_is_multi_use(self):
        record = ConnRecord(
            my_did=self.test_did,
            state=ConnRecord.State.INVITATION.rfc23,
            invitation_mode=ConnRecord.INVITATION_MODE_MULTI,
        )
        connection_id = await record.save(self.session)
        fetched = await ConnRecord.retrieve_by_id(self.session, connection_id)

        assert fetched.is_multiuse_invitation is True

    async def test_attach_retrieve_invitation(self):
        record = ConnRecord(
            my_did=self.test_did,
            state=ConnRecord.State.INVITATION.rfc23,
        )
        connection_id = await record.save(self.session)

        invi = ConnectionInvitation(
            label="abc123",
            recipient_keys=[self.test_verkey],
            endpoint="http://localhost:8999",
        )
        await record.attach_invitation(self.session, invi)
        retrieved = await record.retrieve_invitation(self.session)
        assert isinstance(retrieved, ConnectionInvitation)

    async def test_attach_retrieve_request(self):
        record = ConnRecord(
            my_did=self.test_did,
            state=ConnRecord.State.INVITATION.rfc23,
        )
        connection_id = await record.save(self.session)

        req = ConnectionRequest(
            connection=ConnectionDetail(
                did=self.test_did, did_doc=DIDDoc(self.test_did)
            ),
            label="abc123",
        )
        await record.attach_request(self.session, req)
        retrieved = await record.retrieve_request(self.session)
        assert isinstance(retrieved, ConnectionRequest)

    async def test_deser_old_style_record(self):
        record = ConnRecord(
            state=ConnRecord.State.INIT,
            my_did=self.test_did,
            their_role=ConnRecord.Role.REQUESTER,
        )
        ser = record.serialize()
        ser["initiator"] = "self"  # redundant vs. role as per RFC 160 or RFC 23
        deser = ConnRecord.deserialize(ser)
        reser = deser.serialize()
        assert "initiator" not in reser
