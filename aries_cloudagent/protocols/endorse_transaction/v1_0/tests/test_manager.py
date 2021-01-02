from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from .....core.in_memory import InMemoryProfile
from .....wallet.in_memory import InMemoryWallet

from ..manager import TransactionManager
from ..models.transaction_record import TransactionRecord
from .....connections.models.conn_record import ConnRecord

from ..messages.transaction_request import TransactionRequest


class TestTransactionManager(AsyncTestCase):
    async def setUp(self):
        
        self.session = InMemoryProfile.test_session()
        self.profile = self.session.profile

        self.test_connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"
        self.test_receivers_connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa7"

        self.session.connection_record = ConnRecord(connection_id=self.test_receivers_connection_id)

        self.test_author_did = "55GkHamhTU1ZbTbV2ab9DE"
        self.test_author_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        self.test_endorser_did = "GbuDUYXaUZRfHD2jeDuQuP"
        self.test_endorser_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
        self.test_refuser_did = "GbuDUYXaUZRfHD2jeDuQuP"
        self.test_transaction_message = {
                "attributes": [
                    "score"
                ],
                "schema_name": "prefs",
                "schema_version": "1.0"
                }
        self.test_mechanism="manual"
        self.test_taaDigest="f50feca75664270842bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62"
        self.test_time=1597708800
        self.test_expires_time="2020-12-13T17:29:06+0000"
        self.test_connection_id="3fa85f64-5717-4562-b3fc-2c963f66afa6"

        self.test_request_type = "http://didcomm.org/sign-attachment/%VER/signature-request"
        self.test_response_type = "http://didcomm.org/sign-attachment/%VER/signature-response"

        self.test_signature_request = {
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
            "author_goal_code": TransactionRecord.WRITE_TRANSACTION,
        }

        self.test_format = TransactionRecord.FORMAT_VERSION        

        self.manager = TransactionManager(self.session, self.profile)

        assert self.manager.session
        assert self.manager.profile

    async def test_create_record(self):

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_record = await self.manager.create_record(
                author_did=self.test_author_did,
                author_verkey=self.test_author_verkey,
                transaction_message=self.test_transaction_message,
                mechanism=self.test_mechanism,
                taaDigest=self.test_taaDigest,
                time=self.test_time,
                expires_time=self.test_expires_time
            )
            save_record.assert_called_once()
        
        
        assert transaction_record._type == self.test_request_type
        assert transaction_record.signature_request[0] == self.test_signature_request
        assert transaction_record.timing == {
            "expires_time" : self.test_expires_time
        }
        assert transaction_record.formats[0]["format"] == self.test_format
        
        assert transaction_record.messages_attach[0]["data"]["json"]["identifier"] == self.test_author_did
        assert transaction_record.messages_attach[0]["data"]["json"]["signatures"] == {
            self.test_author_did : self.test_author_verkey
        }
        assert transaction_record.messages_attach[0]["data"]["json"]["operation"]["data"] == self.test_transaction_message
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["mechanism"] == self.test_mechanism
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["taaDigest"] == self.test_taaDigest
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["time"] == self.test_time
        assert transaction_record.state == "created"
        

    async def test_create_request(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )
    
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record, 
                transaction_request
            ) = await self.manager.create_request(transaction_record, self.test_connection_id)
            save_record.assert_called_once()

        assert transaction_record.state == "request"
        assert transaction_record.connection_id == self.test_connection_id

        assert transaction_request.transaction_id == transaction_record._id
        assert transaction_request.signature_request == transaction_record.signature_request[0]
        assert transaction_request.timing == transaction_record.timing
        assert transaction_request.messages_attach == transaction_record.messages_attach[0]


    async def test_receive_request(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        transaction_request = TransactionRequest(
            transaction_id=transaction_record._id,
            signature_request=transaction_record.signature_request[0],
            timing=transaction_record.timing,
            messages_attach=transaction_record.messages_attach[0],
        )

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:            
            transaction_record = await self.manager.receive_request(transaction_request)
            save_record.assert_called_once()

        assert transaction_record._type == self.test_request_type
        assert transaction_record.signature_request[0] == self.test_signature_request
        assert transaction_record.timing == {
            "expires_time" : self.test_expires_time
        }
        assert transaction_record.formats[0]["format"] == self.test_format

        assert transaction_record.messages_attach[0]["data"]["json"]["identifier"] == self.test_author_did
        assert transaction_record.messages_attach[0]["data"]["json"]["signatures"] == {
            self.test_author_did : self.test_author_verkey
        }
        assert transaction_record.messages_attach[0]["data"]["json"]["operation"]["data"] == self.test_transaction_message
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["mechanism"] == self.test_mechanism
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["taaDigest"] == self.test_taaDigest
        assert transaction_record.messages_attach[0]["data"]["json"]["taaAcceptance"]["time"] == self.test_time

        assert transaction_record.thread_id == transaction_request.transaction_id
        assert transaction_record.connection_id == self.test_receivers_connection_id
        assert transaction_record.state == "request"

    async def test_create_endorse_response(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record, 
                endorsed_response
            ) = await self.manager.create_endorse_response(
                                    transaction_record,
                                    state="endorsed",
                                    endorser_did=self.test_endorser_did,
                                    endorser_verkey=self.test_endorser_verkey,
                                )
            save_record.assert_called_once() 

        assert transaction_record.messages_attach[0]["data"]["json"]["endorser"] == self.test_endorser_did
        assert transaction_record._type == self.test_response_type
        assert transaction_record.signature_response[0] == {
            "message_id": transaction_record.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signature": {self.test_endorser_did: self.test_endorser_verkey},
        }
        assert transaction_record.state == "endorsed"

        assert endorsed_response.transaction_id == transaction_record.thread_id
        assert endorsed_response.thread_id == transaction_record._id
        assert endorsed_response.signature_response == {
            "message_id": transaction_record.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signature": {self.test_endorser_did: self.test_endorser_verkey},
        }
        assert endorsed_response.state == "endorsed"
        assert endorsed_response.endorser_did == self.test_endorser_did

    async def test_receive_endorse_response(self):

        transaction_author_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        transaction_author_request = TransactionRequest(
            transaction_id=transaction_author_record._id,
            signature_request=transaction_author_record.signature_request[0],
            timing=transaction_author_record.timing,
            messages_attach=transaction_author_record.messages_attach[0],
        )

        transaction_endorser_record = await self.manager.receive_request(transaction_author_request)

        (
            transaction_author_record,
            endorsed_transaction_response
        ) = await self.manager.create_endorse_response(
                                    transaction_author_record,
                                    state="endorsed",
                                    endorser_did=self.test_endorser_did,
                                    endorser_verkey=self.test_endorser_verkey,
                                )

        endorsed_transaction_response.transaction_id = transaction_endorser_record ._id
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:           
            transaction_endorser_record = await self.manager.receive_endorse_response(
                                            endorsed_transaction_response
                                            )

            save_record.assert_called_once()

        assert transaction_endorser_record._type == self.test_response_type
        assert transaction_endorser_record.state == endorsed_transaction_response.state
        assert transaction_endorser_record.signature_response[0] == endorsed_transaction_response.signature_response
        assert transaction_endorser_record.thread_id == endorsed_transaction_response.thread_id
        assert transaction_endorser_record.messages_attach[0]["data"]["json"]["endorser"] == self.test_endorser_did

    async def test_create_refuse_response(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record, 
                refused_response
            ) = await self.manager.create_refuse_response(
                                    transaction_record,
                                    state="refused",
                                    refuser_did=self.test_refuser_did,
                                )
            save_record.assert_called_once()

        assert transaction_record.messages_attach[0]["data"]["json"]["endorser"] == self.test_refuser_did
        assert transaction_record._type == self.test_response_type
        assert transaction_record.signature_response[0] == {
            "message_id": transaction_record.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION,
        }
        assert transaction_record.state == "refused"

        assert refused_response.transaction_id == transaction_record.thread_id
        assert refused_response.thread_id == transaction_record._id
        assert refused_response.signature_response == {
            "message_id": transaction_record.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION,
        }
        assert refused_response.state == "refused"
        assert refused_response.endorser_did == self.test_refuser_did

    async def test_receive_refuse_response(self):

        transaction_author_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        transaction_author_request = TransactionRequest(
            transaction_id=transaction_author_record._id,
            signature_request=transaction_author_record.signature_request[0],
            timing=transaction_author_record.timing,
            messages_attach=transaction_author_record.messages_attach[0],
        )

        transaction_refuser_record = await self.manager.receive_request(transaction_author_request)

        (
            transaction_author_record,
            refused_transaction_response
        ) = await self.manager.create_refuse_response(
                                    transaction_author_record,
                                    state="refused",
                                    refuser_did=self.test_refuser_did,
                                )

        refused_transaction_response.transaction_id = transaction_refuser_record ._id

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:           
            transaction_refuser_record = await self.manager.receive_refuse_response(
                                            refused_transaction_response
                                            )

            save_record.assert_called_once()

        assert transaction_refuser_record._type == self.test_response_type
        assert transaction_refuser_record.state == refused_transaction_response.state
        assert transaction_refuser_record.signature_response[0] == refused_transaction_response.signature_response
        assert transaction_refuser_record.thread_id == refused_transaction_response.thread_id
        assert transaction_refuser_record.messages_attach[0]["data"]["json"]["endorser"] == self.test_refuser_did

    async def test_cancel_transaction(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record, 
                cancelled_transaction_response
            ) = await self.manager.cancel_transaction(transaction_record, state="cancelled")
            save_record.assert_called_once()

        assert transaction_record.state == "cancelled"

        assert cancelled_transaction_response.state == "cancelled"
        assert cancelled_transaction_response.thread_id == transaction_record._id

    async def test_receive_cancel_transaction(self):

        transaction_sender_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        transaction_sender_request = TransactionRequest(
            transaction_id=transaction_sender_record._id,
            signature_request=transaction_sender_record.signature_request[0],
            timing=transaction_sender_record.timing,
            messages_attach=transaction_sender_record.messages_attach[0],
        )

        transaction_receiver_record = await self.manager.receive_request(transaction_sender_request)

        (
            transaction_sender_record, 
            cancelled_transaction_response
        ) = await self.manager.cancel_transaction(transaction_sender_record, state="cancelled")

        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_receiver_record = await self.manager.receive_cancel_transaction(cancelled_transaction_response)
            save_record.assert_called_once()

        assert transaction_receiver_record.state == "cancelled"

    async def test_transaction_resend(self):

        transaction_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record, 
                resend_transaction_response
            ) = await self.manager.transaction_resend(transaction_record, state="resend")
            save_record.assert_called_once()

        assert transaction_record.state == "resend"

        assert resend_transaction_response.state == "resend"
        assert resend_transaction_response.thread_id == transaction_record._id

    async def test_receive_transaction_resend(self):

        transaction_sender_record = await self.manager.create_record(
            author_did=self.test_author_did,
            author_verkey=self.test_author_verkey,
            transaction_message=self.test_transaction_message,
            mechanism=self.test_mechanism,
            taaDigest=self.test_taaDigest,
            time=self.test_time,
            expires_time=self.test_expires_time
        )

        transaction_sender_request = TransactionRequest(
            transaction_id=transaction_sender_record._id,
            signature_request=transaction_sender_record.signature_request[0],
            timing=transaction_sender_record.timing,
            messages_attach=transaction_sender_record.messages_attach[0],
        )

        transaction_receiver_record = await self.manager.receive_request(transaction_sender_request)

        (
            transaction_sender_record, 
            resend_transaction_response
        ) = await self.manager.transaction_resend(transaction_sender_record, state="resend")

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_receiver_record = await self.manager.receive_transaction_resend(resend_transaction_response)
            save_record.assert_called_once()

        assert transaction_receiver_record.state == "resend"