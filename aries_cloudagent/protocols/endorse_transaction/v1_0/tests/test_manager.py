from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
from .....core.in_memory import InMemoryProfile
from .....wallet.in_memory import InMemoryWallet

from ..manager import TransactionManager, TransactionManagerError
from ..models.transaction_record import TransactionRecord
from .....connections.models.conn_record import ConnRecord
from ..messages.messages_attach import MessagesAttach

from ..messages.transaction_request import TransactionRequest
import uuid


class TestTransactionManager(AsyncTestCase):
    async def setUp(self):

        self.session = InMemoryProfile.test_session()

        self.test_messages_attach = """{
	                                    "endorser": "DJGEjaMunDtFtBVrn1qJMT",
	                                    "identifier": "C3nJhruVc7feyB6ckJwhi2",
	                                    "operation": {
		                                                "data": {
			                                                    "attr_names": ["score"],
			                                                    "name": "prefs",
			                                                    "version": "1.0"
		                                                        },
		                                                "type": "101"
	                                                },
	                                    "protocolVersion": 2,
	                                    "reqId": 1613463373859595201,
	                                    "signatures": {
		                                                "C3nJhruVc7feyB6ckJwhi2": "2iNTeFy44WK9zpsPfcwfu489aHWroYh3v8mme9tPyNKncrk1tVbWKNU4zFvLAbSBwHWxShQSJrhRgoxwaehCaz2j"
	                                                  }
                                    }"""

        self.test_expires_time = "1597708800"
        self.test_connection_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        self.test_receivers_connection_id = "3fa85f64-5717-4562-b3fc-2c963f66afa7"  
        self.test_author_transaction_id = "3fa85f64-5717-4562-b3fc-2c963f66afa7"
        self.test_endorser_transaction_id = "3fa85f64-5717-4562-b3fc-2c963f66afa8"

        self.test_endorsed_message = """{
	                                    "endorser": "DJGEjaMunDtFtBVrn1qJMT",
	                                    "identifier": "C3nJhruVc7feyB6ckJwhi2",
	                                    "operation": {
		                                                "data": {
			                                                    "attr_names": ["score"],
			                                                    "name": "prefs",
			                                                    "version": "1.0"
		                                                        },
		                                                "type": "101"
	                                                },
	                                    "protocolVersion": 2,
	                                    "reqId": 1613463373859595201,
	                                    "signatures": {
		                                                "C3nJhruVc7feyB6ckJwhi2": "2iNTeFy44WK9zpsPfcwfu489aHWroYh3v8mme9tPyNKncrk1tVbWKNU4zFvLAbSBwHWxShQSJrhRgoxwaehCaz2j",
		                                                "DJGEjaMunDtFtBVrn1qJMT": "3hPr2WgAixcXQRQfCZKnmpY7SkQyQW4cegX7QZMPv6FvsNRFV7yW21VaFC5CA3Aze264dkHjX4iZ1495am8fe1qZ"
	                                                  }
                                    }""" 

        self.test_signature = """{
	                                    "endorser": "DJGEjaMunDtFtBVrn1qJMT",
	                                    "identifier": "C3nJhruVc7feyB6ckJwhi2",
	                                    "operation": {
		                                                "data": {
			                                                    "attr_names": ["score"],
			                                                    "name": "prefs",
			                                                    "version": "1.0"
		                                                        },
		                                                "type": "101"
	                                                },
	                                    "protocolVersion": 2,
	                                    "reqId": 1613463373859595201,
	                                    "signatures": {
		                                                "C3nJhruVc7feyB6ckJwhi2": "2iNTeFy44WK9zpsPfcwfu489aHWroYh3v8mme9tPyNKncrk1tVbWKNU4zFvLAbSBwHWxShQSJrhRgoxwaehCaz2j",
		                                                "DJGEjaMunDtFtBVrn1qJMT": "3hPr2WgAixcXQRQfCZKnmpY7SkQyQW4cegX7QZMPv6FvsNRFV7yW21VaFC5CA3Aze264dkHjX4iZ1495am8fe1qZ"
	                                                  }
                                    }"""
        self.test_endorser_did = "DJGEjaMunDtFtBVrn1qJMT"
        self.test_endorser_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        self.test_refuser_did = "AGDEjaMunDtFtBVrn1qPKQ"




        #self.profile = self.session.profile

        
        

        #self.session.connection_record = ConnRecord(
        #    connection_id=self.test_receivers_connection_id
        #)

        #self.test_author_did = "55GkHamhTU1ZbTbV2ab9DE"
        #self.test_author_verkey = "3Dn1SJNPaCXcvvJvSbsFWP2xaCjMom3can8CQNhWrTRx"
        #self.test_endorser_did = "GbuDUYXaUZRfHD2jeDuQuP"
        #self.test_endorser_verkey = "9WCgWKUaAJj3VWxxtzvvMQN3AoFxoBtBDo9ntwJnVVCC"
        #self.test_refuser_did = "GbuDUYXaUZRfHD2jeDuQuP"
        #self.test_transaction_message = {
        #    "attributes": ["score"],
        #    "schema_name": "prefs",
        #    "schema_version": "1.0",
        #}
        #self.test_mechanism = "manual"
        #self.test_taaDigest = (
        #    "f50feca75664270842bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62"
        #)
        #self.test_time = 1597708800
        #self.test_expires_time = "2020-12-13T17:29:06+0000"
        #self.test_connection_id = "3fa85f64-5717-4562-b3fc-2c963f66afa6"

        #self.test_request_type = (
        #    "http://didcomm.org/sign-attachment/%VER/signature-request"
        #)
        #self.test_response_type = (
        #    "http://didcomm.org/sign-attachment/%VER/signature-response"
        #)

        #self.test_signature_request = {
        #    "context": TransactionRecord.SIGNATURE_CONTEXT,
        #    "method": TransactionRecord.ADD_SIGNATURE,
        #    "signature_type": TransactionRecord.SIGNATURE_TYPE,
        #    "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
        #    "author_goal_code": TransactionRecord.WRITE_TRANSACTION,
        #}

        #self.test_format = TransactionRecord.FORMAT_VERSION

        self.manager = TransactionManager(self.session)

        assert self.manager.session


    async def test_create_record(self):

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_record = await self.manager.create_record(
                messages_attach=self.test_messages_attach,
                expires_time=self.test_expires_time
            )
            save_record.assert_called_once()

            assert transaction_record.timing["expires_time"] == self.test_expires_time
            assert transaction_record.formats[0]["attach_id"] == transaction_record.messages_attach[0]["@id"]
            assert transaction_record.formats[0]["format"] == TransactionRecord.FORMAT_VERSION
            assert transaction_record.messages_attach[0]["data"]["json"] == self.test_messages_attach
            assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_CREATED

    async def test_create_request_bad_state(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_ENDORSED

        with self.assertRaises(TransactionManagerError):
            await self.manager.create_request(
                transaction=transaction_record,
                connection_id=self.test_connection_id
            )


    async def test_create_request(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record,
                transaction_request,
            ) = await self.manager.create_request(
                transaction_record, self.test_connection_id
            )
            save_record.assert_called_once()
        
        assert transaction_record._type == TransactionRecord.SIGNATURE_REQUEST
        assert transaction_record.signature_request[0] == {
                            "context": TransactionRecord.SIGNATURE_CONTEXT,
                            "method": TransactionRecord.ADD_SIGNATURE,
                            "signature_type": TransactionRecord.SIGNATURE_TYPE,
                            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                            "author_goal_code": TransactionRecord.WRITE_TRANSACTION,
                        }
        assert transaction_record.state == TransactionRecord.STATE_REQUEST_SENT
        assert transaction_record.connection_id == self.test_connection_id

        assert transaction_request.transaction_id == transaction_record._id
        assert (
            transaction_request.signature_request
            == transaction_record.signature_request[0]
        )
        assert transaction_request.timing == transaction_record.timing
        assert (
            transaction_request.messages_attach == transaction_record.messages_attach[0]
        )

    async def test_recieve_request(self):
        
        mock_request = async_mock.MagicMock()
        mock_request.transaction_id = self.test_author_transaction_id
        mock_request.signature_request = {
                            "context": TransactionRecord.SIGNATURE_CONTEXT,
                            "method": TransactionRecord.ADD_SIGNATURE,
                            "signature_type": TransactionRecord.SIGNATURE_TYPE,
                            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                            "author_goal_code": TransactionRecord.WRITE_TRANSACTION,
                        }
        mock_request.messages_attach = {
                            "@id": str(uuid.uuid4()),
                            "mime-type": "application/json",
                            "data": {"json": self.test_messages_attach}
                        }
        mock_request.timing = {
                            "expires_time" : self.test_expires_time
                        }

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_record = await self.manager.receive_request(mock_request, self.test_receivers_connection_id)
            save_record.assert_called_once()

        assert transaction_record._type == TransactionRecord.SIGNATURE_REQUEST
        assert transaction_record.signature_request[0] == mock_request.signature_request
        assert transaction_record.timing == mock_request.timing
        assert transaction_record.formats[0] == {
                                    "attach_id": mock_request.messages_attach["@id"],
                                    "format": TransactionRecord.FORMAT_VERSION,
                                }
        assert transaction_record.messages_attach[0] == mock_request.messages_attach
        assert transaction_record.thread_id == self.test_author_transaction_id
        assert transaction_record.connection_id == self.test_receivers_connection_id
        assert transaction_record.state == TransactionRecord.STATE_REQUEST_RECEIVED

    async def test_create_endorse_response_bad_state(self):
        
        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_ENDORSED

        with self.assertRaises(TransactionManagerError):
            await self.manager.create_endorse_response(
                transaction=transaction_record,
                state=TransactionRecord.STATE_TRANSACTION_ENDORSED,
                endorser_did=self.test_endorser_did,
                endorser_verkey=self.test_endorser_verkey,
                endorsed_msg=self.test_endorsed_message,
                signature=self.test_signature
            )

    async def test_create_endorse_response(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_REQUEST_RECEIVED
        transaction_record.thread_id = self.test_author_transaction_id
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record,
                endorsed_transaction_response,
            ) = await self.manager.create_endorse_response(
                transaction_record, 
                state=TransactionRecord.STATE_TRANSACTION_ENDORSED,
                endorser_did=self.test_endorser_did,
                endorser_verkey=self.test_endorser_verkey,
                endorsed_msg=self.test_endorsed_message,
                signature=self.test_signature
            )
            save_record.assert_called_once()
        
        
        assert transaction_record._type == TransactionRecord.SIGNATURE_RESPONSE
        assert transaction_record.messages_attach[0]["data"]["json"] == self.test_endorsed_message
        assert transaction_record.signature_response[0] == {
                                            "message_id": transaction_record.messages_attach[0]["@id"],
                                            "context": TransactionRecord.SIGNATURE_CONTEXT,
                                            "method": TransactionRecord.ADD_SIGNATURE,
                                            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                                            "signature_type": TransactionRecord.SIGNATURE_TYPE,
                                            "signature": {self.test_endorser_did: self.test_signature},
                                        }
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_ENDORSED

        assert endorsed_transaction_response.transaction_id == self.test_author_transaction_id
        assert endorsed_transaction_response.thread_id == transaction_record._id
        assert endorsed_transaction_response.signature_response == {
                                                                    "message_id": transaction_record.messages_attach[0]["@id"],
                                                                    "context": TransactionRecord.SIGNATURE_CONTEXT,
                                                                    "method": TransactionRecord.ADD_SIGNATURE,
                                                                    "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                                                                    "signature_type": TransactionRecord.SIGNATURE_TYPE,
                                                                    "signature": {self.test_endorser_did : self.test_signature},
                                                                }
                                                                
        assert endorsed_transaction_response.state == TransactionRecord.STATE_TRANSACTION_ENDORSED
        assert endorsed_transaction_response.endorser_did == self.test_endorser_did

    async def test_receive_endorse_response(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        self.test_author_transaction_id = transaction_record._id

        mock_response = async_mock.MagicMock()
        mock_response.transaction_id = self.test_author_transaction_id
        mock_response.thread_id = self.test_endorser_transaction_id
        mock_response.signature_response = {
                                "message_id": transaction_record.messages_attach[0]["@id"],
                                "context": TransactionRecord.SIGNATURE_CONTEXT,
                                "method": TransactionRecord.ADD_SIGNATURE,
                                "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                                "signature_type": TransactionRecord.SIGNATURE_TYPE,
                                "signature": {self.test_endorser_did: self.test_signature},
                            }
        mock_response.state = TransactionRecord.STATE_TRANSACTION_ENDORSED
        mock_response.endorser_did = self.test_endorser_did

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_record = await self.manager.receive_endorse_response(mock_response)
            save_record.assert_called_once()
        
        assert transaction_record._type == TransactionRecord.SIGNATURE_RESPONSE
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_ENDORSED
        assert transaction_record.signature_response[0] == {
                                "message_id": transaction_record.messages_attach[0]["@id"],
                                "context": TransactionRecord.SIGNATURE_CONTEXT,
                                "method": TransactionRecord.ADD_SIGNATURE,
                                "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
                                "signature_type": TransactionRecord.SIGNATURE_TYPE,
                                "signature": {self.test_endorser_did: self.test_signature},
                            }
        assert transaction_record.thread_id == self.test_endorser_transaction_id
        assert transaction_record.messages_attach[0]["data"]["json"] == self.test_signature 

    async def test_create_refuse_response_bad_state(self):
        
        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_ENDORSED

        with self.assertRaises(TransactionManagerError):
            await self.manager.create_refuse_response(
                transaction=transaction_record,
                state=TransactionRecord.STATE_TRANSACTION_REFUSED,
                refuser_did=self.test_refuser_did,
            )

    async def test_create_refuse_response(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_REQUEST_RECEIVED
        transaction_record.thread_id = self.test_author_transaction_id
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record,
                refused_transaction_response,
            ) = await self.manager.create_refuse_response(
                transaction_record, 
                state=TransactionRecord.STATE_TRANSACTION_REFUSED,
                refuser_did=self.test_refuser_did,
            )
            save_record.assert_called_once()
        
        
        assert transaction_record._type == TransactionRecord.SIGNATURE_RESPONSE
        assert transaction_record.signature_response[0] == {
                                            "message_id": transaction_record.messages_attach[0]["@id"],
                                            "context": TransactionRecord.SIGNATURE_CONTEXT,
                                            "method": TransactionRecord.ADD_SIGNATURE,
                                            "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION,
                                        }
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_REFUSED

        assert refused_transaction_response.transaction_id == self.test_author_transaction_id
        assert refused_transaction_response.thread_id == transaction_record._id
        assert refused_transaction_response.signature_response == {
                                                                    "message_id": transaction_record.messages_attach[0]["@id"],
                                                                    "context": TransactionRecord.SIGNATURE_CONTEXT,
                                                                    "method": TransactionRecord.ADD_SIGNATURE,
                                                                    "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION
                                                                }
                                                                
        assert refused_transaction_response.state == TransactionRecord.STATE_TRANSACTION_REFUSED
        assert refused_transaction_response.endorser_did == self.test_refuser_did

    async def test_receive_refuse_response(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        self.test_author_transaction_id = transaction_record._id

        mock_response = async_mock.MagicMock()
        mock_response.transaction_id = self.test_author_transaction_id
        mock_response.thread_id = self.test_endorser_transaction_id
        mock_response.signature_response = {
                                "message_id": transaction_record.messages_attach[0]["@id"],
                                "context": TransactionRecord.SIGNATURE_CONTEXT,
                                "method": TransactionRecord.ADD_SIGNATURE,
                                "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION
                            }
        mock_response.state = TransactionRecord.STATE_TRANSACTION_REFUSED
        mock_response.endorser_did = self.test_refuser_did

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            transaction_record = await self.manager.receive_refuse_response(mock_response)
            save_record.assert_called_once()
        
        assert transaction_record._type == TransactionRecord.SIGNATURE_RESPONSE
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_REFUSED
        assert transaction_record.signature_response[0] == {
                                "message_id": transaction_record.messages_attach[0]["@id"],
                                "context": TransactionRecord.SIGNATURE_CONTEXT,
                                "method": TransactionRecord.ADD_SIGNATURE,
                                "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION
                            }
        assert transaction_record.thread_id == self.test_endorser_transaction_id

    async def test_cancel_transaction_bad_state(self):
        
        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_ENDORSED

        with self.assertRaises(TransactionManagerError):
            await self.manager.cancel_transaction(
                transaction=transaction_record,
                state=TransactionRecord.STATE_TRANSACTION_CANCELLED
            )

    async def test_cancel_transaction(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_REQUEST_SENT
        transaction_record.thread_id = self.test_endorser_transaction_id
        transaction_record._id = self.test_author_transaction_id
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record,
                cancelled_transaction_response,
            ) = await self.manager.cancel_transaction(
                transaction_record, 
                state=TransactionRecord.STATE_TRANSACTION_CANCELLED
            )
            save_record.assert_called_once()
        
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_CANCELLED

        assert cancelled_transaction_response.thread_id == self.test_author_transaction_id
        assert cancelled_transaction_response.state == TransactionRecord.STATE_TRANSACTION_CANCELLED

    async def test_receive_cancel_transaction(self):

        author_transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        (
                author_transaction_record,
                author_transaction_request,
        ) = await self.manager.create_request(
                author_transaction_record, self.test_connection_id
        )

        endorser_transaction_record = await self.manager.receive_request(
            author_transaction_request, self.test_receivers_connection_id
        )

        mock_response = async_mock.MagicMock()
        mock_response.state = TransactionRecord.STATE_TRANSACTION_CANCELLED
        mock_response.thread_id = author_transaction_record._id

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            endorser_transaction_record = await self.manager.receive_cancel_transaction(
                mock_response, self.test_receivers_connection_id
            )
            save_record.assert_called_once()

        assert endorser_transaction_record.state == TransactionRecord.STATE_TRANSACTION_CANCELLED

    async def test_transaction_resend_bad_state(self):
        
        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_ENDORSED

        with self.assertRaises(TransactionManagerError):
            await self.manager.transaction_resend(
                transaction=transaction_record,
                state=TransactionRecord.STATE_TRANSACTION_RESENT
            )

    async def test_transaction_resend(self):

        transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        transaction_record.state = TransactionRecord.STATE_TRANSACTION_REFUSED
        transaction_record.thread_id = self.test_endorser_transaction_id
        transaction_record._id = self.test_author_transaction_id
        
        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            (
                transaction_record,
                resend_transaction_response,
            ) = await self.manager.transaction_resend(
                transaction_record, 
                state=TransactionRecord.STATE_TRANSACTION_RESENT
            )
            save_record.assert_called_once()
        
        assert transaction_record.state == TransactionRecord.STATE_TRANSACTION_RESENT

        assert resend_transaction_response.thread_id == self.test_author_transaction_id
        assert resend_transaction_response.state == TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED

    async def test_receive_transaction_resend(self):

        author_transaction_record = await self.manager.create_record(
            messages_attach=self.test_messages_attach,
            expires_time=self.test_expires_time
        )
        (
                author_transaction_record,
                author_transaction_request,
        ) = await self.manager.create_request(
                author_transaction_record, self.test_connection_id
        )

        endorser_transaction_record = await self.manager.receive_request(
            author_transaction_request, self.test_receivers_connection_id
        )

        mock_response = async_mock.MagicMock()
        mock_response.state = TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED
        mock_response.thread_id = author_transaction_record._id

        with async_mock.patch.object(
            TransactionRecord, "save", autospec=True
        ) as save_record:
            endorser_transaction_record = await self.manager.receive_transaction_resend(
                mock_response, self.test_receivers_connection_id
            )
            save_record.assert_called_once()

        assert endorser_transaction_record.state == TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED
