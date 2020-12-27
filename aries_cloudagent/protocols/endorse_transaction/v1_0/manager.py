"""Class to manage transactions."""

from aiohttp import web
import logging

from .models.transaction_record import TransactionRecord
from .messages.transaction_request import TransactionRequest
from .messages.endorsed_transaction_response import EndorsedTransactionResponse
from .messages.refused_transaction_response import RefusedTransactionResponse
from .messages.cancel_transaction import CancelTransaction
from .messages.transaction_resend import TransactionResend
from .messages.transaction_job_to_send import TransactionJobToSend
from .messages.messages_attach import MessagesAttach

from ....connections.models.conn_record import ConnRecord
from ....transport.inbound.receipt import MessageReceipt
from ....storage.error import StorageNotFoundError

from ....ledger.base import BaseLedger
from ....core.error import BaseError
from ....core.profile import Profile, ProfileSession
from ....ledger.error import LedgerError

from ....wallet.base import BaseWallet


class TransactionManagerError(BaseError):
    """Transaction error."""


class TransactionManager:
    """Class for managing transactions."""

    def __init__(self, session: ProfileSession, profile: Profile):
        """
        Initialize a TransactionManager.

        Args:
            session: The Profile Session for this transaction manager
            profile: The Profile for this transaction manager
        """
        self._session = session
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    @property
    def session(self) -> ProfileSession:
        """
        Accessor for the current Profile Session.

        Returns:
            The Profile Session for this transaction manager

        """
        return self._session

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current Profile.

        Returns:
            The Profile for this transaction manager

        """
        return self._profile

    async def create_record(
        self,
        expires_time: str = None,
        transaction_message: dict = {},
    ):
        """
        Create a new Transaction Record.

        Args:
            expires_time: The time till which the endorser should endorse the transaction
            transaction_message: The actual data in the transaction payload

        Returns:
            The transaction Record and transaction request

        """

        wallet: BaseWallet = self.session.inject(BaseWallet, required=False)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        author_did_info = await wallet.get_public_did()
        if not author_did_info:
            raise web.HTTPForbidden(reason="Public DID not found in wallet")
        author_did = author_did_info.did
        author_verkey = author_did_info.verkey

        ledger: BaseLedger = self.session.inject(BaseLedger, required=False)

        if not ledger:
            reason = "No indy ledger available"
            if not self.session.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise web.HTTPForbidden(reason=reason)

        async with ledger:
            try:
                taa_info = await ledger.get_txn_author_agreement()
                accepted = None
                if taa_info["taa_required"]:
                    accept_record = await ledger.get_latest_txn_author_acceptance()
                    if accept_record:
                        accepted = {
                            "mechanism": accept_record["mechanism"],
                            "time": accept_record["time"],
                        }
                taa_info["taa_accepted"] = accepted
            except LedgerError as err:
                raise web.HTTPBadRequest(reason=err.roll_up) from err

        if taa_info["taa_accepted"] is not None:
            mechanism = taa_info["taa_accepted"]["mechanism"]
            time = taa_info["taa_accepted"]["time"]
        else:
            mechanism = None
            time = None

        if taa_info["taa_record"] is not None:
            taaDigest = taa_info["taa_record"]["digest"]
        else:
            taaDigest = None

        messages_attach = MessagesAttach(
            author_did=author_did,
            author_verkey=author_verkey,
            transaction_message=transaction_message,
            mechanism=mechanism,
            taaDigest=taaDigest,
            time=time,
        )
        messages_attach_dict = messages_attach.__dict__

        transaction = TransactionRecord()
        transaction._type = TransactionRecord.SIGNATURE_REQUEST

        signature_request = {
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
            "author_goal_code": TransactionRecord.WRITE_TRANSACTION,
        }
        transaction.signature_request.clear()
        transaction.signature_request.append(signature_request)

        timing = {"expires_time": "1597708800"}
        transaction.timing = timing

        formats = {
            "attach_id": messages_attach._id,
            "format": TransactionRecord.FORMAT_VERSION,
        }
        transaction.formats.clear()
        transaction.formats.append(formats)

        transaction.messages_attach.clear()
        transaction.messages_attach.append(messages_attach_dict)
        transaction.state = "created"

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

        return transaction

    async def create_request(
        self, transaction: TransactionRecord, connection_id: str = None
    ):
        """
        Create a new Transaction Request.

        Args:
            transaction: The transaction from which the request is created.
            connection_id: The connection_id to which the request is send.

        Returns:
            The transaction Record and transaction request

        """

        transaction.state = "request"
        transaction.connection_id = connection_id
        async with self._profile.session() as session:
            await transaction.save(session, reason="Change to requested state")

        transaction_request = TransactionRequest(
            transaction_id=transaction._id,
            signature_request=transaction.signature_request[0],
            timing=transaction.timing,
            messages_attach=transaction.messages_attach[0],
        )

        return transaction, transaction_request

    async def receive_request(self, request: TransactionRequest):
        """
        Receive a Transaction request.

        Args:
            request: A Transaction Request
        """

        connection_id = self.session.connection_record.connection_id
        transaction = TransactionRecord()

        transaction._type = TransactionRecord.SIGNATURE_REQUEST
        transaction.signature_request.clear()
        transaction.signature_request.append(request.signature_request)
        transaction.timing = request.timing

        format = {
            "attach_id": request.messages_attach["_message_id"],
            "format": TransactionRecord.FORMAT_VERSION,
        }
        transaction.formats.clear()
        transaction.formats.append(format)

        transaction.messages_attach.clear()
        transaction.messages_attach.append(request.messages_attach)
        transaction.thread_id = request.transaction_id
        transaction.connection_id = connection_id
        transaction.state = "request"

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

    async def create_endorse_response(
        self, transaction: TransactionRecord = None, state: str = None
    ):
        """
        Create a response to endorse a transaction.

        Args:
            transaction: The transaction record which would be endorsed.
            state: The state of the transaction record

        Returns:
            The updated transaction and an endorsed response

        """

        wallet: BaseWallet = self.session.inject(BaseWallet, required=False)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        endorser_did_info = await wallet.get_public_did()
        if not endorser_did_info:
            raise web.HTTPForbidden(reason="Public DID not found in wallet")
        endorser_did = endorser_did_info.did
        endorser_verkey = endorser_did_info.verkey

        transaction.messages_attach[0]["data"]["json"]["endorser"] = endorser_did

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE

        signature_response = {
            "message_id": transaction.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.ENDORSE_TRANSACTION,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signature": {endorser_did: endorser_verkey},
        }
        transaction.signature_response.clear()
        transaction.signature_response.append(signature_response)

        transaction.state = state

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

        endorsed_transaction_response = EndorsedTransactionResponse(
            transaction_id=transaction.thread_id,
            thread_id=transaction._id,
            signature_response=signature_response,
            state=state,
            endorser_did=endorser_did,
        )

        return transaction, endorsed_transaction_response

    async def receive_endorse_response(self, response: EndorsedTransactionResponse):
        """
        Update the transaction record with the endorsed response.

        Args:
            response: The Endorsed Transaction Response
        """

        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, response.transaction_id
            )

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE
        transaction.state = response.state

        transaction.signature_response.clear()
        transaction.signature_response.append(response.signature_response)

        transaction.thread_id = response.thread_id
        transaction.messages_attach[0]["data"]["json"][
            "endorser"
        ] = response.endorser_did

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

    async def create_refuse_response(
        self, transaction: TransactionRecord = None, state: str = None
    ):
        """
        Create a response to refuse a transaction.

        Args:
            transaction: The transaction record which would be refused
            state: The state of the transaction record

        Returns:
            The updated transaction and the refused response

        """

        wallet: BaseWallet = self.session.inject(BaseWallet, required=False)
        if not wallet:
            raise web.HTTPForbidden(reason="No wallet available")
        endorser_did_info = await wallet.get_public_did()
        if not endorser_did_info:
            raise web.HTTPForbidden(reason="Public DID not found in wallet")
        endorser_did = endorser_did_info.did

        transaction.messages_attach[0]["data"]["json"]["endorser"] = endorser_did

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE

        signature_response = {
            "message_id": transaction.messages_attach[0]["_message_id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION,
        }
        transaction.signature_response.clear()
        transaction.signature_response.append(signature_response)

        transaction.state = state

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

        refused_transaction_response = RefusedTransactionResponse(
            transaction_id=transaction.thread_id,
            thread_id=transaction._id,
            signature_response=signature_response,
            state=state,
            endorser_did=endorser_did,
        )

        return transaction, refused_transaction_response

    async def receive_refuse_response(self, response: RefusedTransactionResponse):
        """
        Update the transaction record with a refused response.

        Args:
            response: The refused transaction response
        """

        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_id(
                session, response.transaction_id
            )

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE
        transaction.state = response.state

        transaction.signature_response.clear()
        transaction.signature_response.append(response.signature_response)
        transaction.thread_id = response.thread_id
        transaction.messages_attach[0]["data"]["json"][
            "endorser"
        ] = response.endorser_did

        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

    async def cancel_transaction(
        self, transaction: TransactionRecord = None, state: str = None
    ):
        """
        Cancel a Transaction Request.

        Args:
            transaction: The transaction record which would be cancelled
            state: The state of the transaction record

        Returns:
            The updated transaction and the cancelled transaction response

        """

        transaction.state = state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

        cancelled_transaction_response = CancelTransaction(
            state="cancelled", thread_id=transaction._id
        )

        return transaction, cancelled_transaction_response

    async def receive_cancel_transaction(self, response: CancelTransaction):
        """
        Update the transaction record to cancel a transaction request.

        Args:
            response: The cancel transaction response
        """
        connection_id = self.session.connection_record.connection_id
        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_connection_and_thread(
                session, connection_id, response.thread_id
            )

        transaction.state = response.state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

    async def transaction_resend(
        self, transaction: TransactionRecord = None, state: str = None
    ):
        """
        Resend a transaction request.

        Args:
            transaction: The transaction record which needs to be resend
            state: the state of the transaction record

        Returns:
            The updated transaction and the resend response

        """

        transaction.state = state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

        resend_transaction_response = TransactionResend(
            state="resend", thread_id=transaction._id
        )

        return transaction, resend_transaction_response

    async def receive_transaction_resend(self, response: TransactionResend):
        """
        Update the transaction with a resend request.

        Args:
            response: The Resend transaction response
        """
        connection_id = self.session.connection_record.connection_id
        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_connection_and_thread(
                session, connection_id, response.thread_id
            )

        transaction.state = response.state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Change it")

    async def set_transaction_my_job(self, record: ConnRecord, transaction_my_job: str):
        """
        Set transaction_my_job.

        Args:
            record: The connection record in which to set transaction jobs
            transaction_my_job: My transaction job

        Returns:
            The transaction job that is send to other agent

        """

        value = await record.metadata_get(self._session, "transaction_jobs")

        if value:
            value["transaction_my_job"] = transaction_my_job
        else:
            value = {"transaction_my_job": transaction_my_job}
        await record.metadata_set(self._session, key="transaction_jobs", value=value)

        tx_job_to_send = TransactionJobToSend(job=transaction_my_job)
        return tx_job_to_send

    async def set_transaction_their_job(
        self, tx_job_received: TransactionJobToSend, receipt: MessageReceipt
    ):
        """
        Set transaction_their_job.

        Args:
            tx_job_received: The transaction job that is received from the other agent
            receipt: The Message Receipt Object
        """

        try:
            connection = await ConnRecord.retrieve_by_did(
                self._session, receipt.sender_did, receipt.recipient_did
            )
        except StorageNotFoundError as err:
            raise web.HTTPNotFound(reason=err.roll_up) from err

        value = await connection.metadata_get(self._session, "transaction_jobs")
        if value:
            value["transaction_their_job"] = tx_job_received.job
        else:
            value = {"transaction_their_job": tx_job_received.job}
        await connection.metadata_set(
            self._session, key="transaction_jobs", value=value
        )
