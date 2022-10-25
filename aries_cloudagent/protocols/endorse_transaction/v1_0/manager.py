"""Class to manage transactions."""

import json
import logging
import uuid

from asyncio import shield

from ....connections.models.conn_record import ConnRecord
from ....core.error import BaseError
from ....core.profile import Profile
from ....indy.issuer import IndyIssuerError
from ....ledger.base import BaseLedger
from ....ledger.error import LedgerError
from ....messaging.credential_definitions.util import notify_cred_def_event
from ....messaging.schemas.util import notify_schema_event
from ....revocation.util import (
    notify_revocation_reg_endorsed_event,
    notify_revocation_entry_endorsed_event,
)
from ....storage.error import StorageError, StorageNotFoundError
from ....transport.inbound.receipt import MessageReceipt
from ....wallet.base import BaseWallet
from ....wallet.util import (
    notify_endorse_did_event,
    notify_endorse_did_attrib_event,
)

from .messages.cancel_transaction import CancelTransaction
from .messages.endorsed_transaction_response import EndorsedTransactionResponse
from .messages.refused_transaction_response import RefusedTransactionResponse
from .messages.transaction_acknowledgement import TransactionAcknowledgement
from .messages.transaction_job_to_send import TransactionJobToSend
from .messages.transaction_request import TransactionRequest
from .messages.transaction_resend import TransactionResend
from .models.transaction_record import TransactionRecord
from .transaction_jobs import TransactionJob


class TransactionManagerError(BaseError):
    """Transaction error."""


class TransactionManager:
    """Class for managing transactions."""

    def __init__(self, profile: Profile):
        """
        Initialize a TransactionManager.

        Args:
            session: The Profile Session for this transaction manager
        """
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    @property
    def profile(self) -> Profile:
        """
        Accessor for the current Profile.

        Returns:
            The Profile for this transaction manager

        """
        return self._profile

    async def create_record(
        self, messages_attach: str, connection_id: str, meta_data: dict = None
    ):
        """
        Create a new Transaction Record.

        Args:
            messages_attach: messages to attach, JSON-dumped
            connection_id: The connection_id of the ConnRecord between author and endorser

        Returns:
            The transaction Record

        """

        messages_attach_dict = {
            "@id": str(uuid.uuid4()),
            "mime-type": "application/json",
            "data": {"json": messages_attach},
        }

        transaction = TransactionRecord()

        formats = {
            "attach_id": messages_attach_dict["@id"],
            "format": TransactionRecord.FORMAT_VERSION,
        }
        transaction.formats.clear()
        transaction.formats.append(formats)

        transaction.messages_attach.clear()
        transaction.messages_attach.append(messages_attach_dict)

        if meta_data:
            transaction.meta_data = meta_data

        transaction.state = TransactionRecord.STATE_TRANSACTION_CREATED
        transaction.connection_id = connection_id

        async with self._profile.session() as session:
            await transaction.save(session, reason="Created a Transaction Record")

        return transaction

    # todo - implementing changes for writing final transaction to the ledger
    # (For Sign Transaction Protocol)
    async def create_request(
        self,
        transaction: TransactionRecord,
        signature: str = None,
        signed_request: dict = None,
        expires_time: str = None,
        endorser_write_txn: bool = None,
        author_goal_code: str = None,
        signer_goal_code: str = None,
    ):
        """
        Create a new Transaction Request.

        Args:
            transaction: The transaction from which the request is created.
            expires_time: The time till which the endorser should endorse the transaction.

        Returns:
            The transaction Record and transaction request

        """

        if transaction.state != TransactionRecord.STATE_TRANSACTION_CREATED:
            raise TransactionManagerError(
                f"Cannot create a request for transaction record"
                f" in state: {transaction.state}"
            )

        transaction._type = TransactionRecord.SIGNATURE_REQUEST
        signature_request = {
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signer_goal_code": signer_goal_code
            if signer_goal_code
            else TransactionRecord.ENDORSE_TRANSACTION,
            "author_goal_code": author_goal_code
            if author_goal_code
            else TransactionRecord.WRITE_TRANSACTION,
        }
        transaction.signature_request.clear()
        transaction.signature_request.append(signature_request)

        transaction.state = TransactionRecord.STATE_REQUEST_SENT

        timing = {"expires_time": expires_time}
        transaction.timing = timing
        transaction.endorser_write_txn = endorser_write_txn

        async with self._profile.session() as session:
            await transaction.save(session, reason="Created an endorsement request")

        transaction_request = TransactionRequest(
            transaction_id=transaction._id,
            signature_request=transaction.signature_request[0],
            timing=transaction.timing,
            messages_attach=transaction.messages_attach[0],
            endorser_write_txn=endorser_write_txn,
        )

        return transaction, transaction_request

    async def receive_request(self, request: TransactionRequest, connection_id: str):
        """
        Receive a Transaction request.

        Args:
            request: A Transaction Request
            connection_id: The connection id related to this transaction record
        """

        transaction = TransactionRecord()

        transaction._type = TransactionRecord.SIGNATURE_REQUEST
        transaction.signature_request.clear()
        transaction.signature_request.append(request.signature_request)
        transaction.timing = request.timing

        format = {
            "attach_id": request.messages_attach["@id"],
            "format": TransactionRecord.FORMAT_VERSION,
        }
        transaction.formats.clear()
        transaction.formats.append(format)

        transaction.messages_attach.clear()
        transaction.messages_attach.append(request.messages_attach)
        transaction.thread_id = request.transaction_id
        transaction.connection_id = connection_id
        transaction.state = TransactionRecord.STATE_REQUEST_RECEIVED
        transaction.endorser_write_txn = request.endorser_write_txn

        async with self._profile.session() as session:
            await transaction.save(session, reason="Received an endorsement request")

        return transaction

    # todo - implementing changes for writing final transaction to the ledger
    # (For Sign Transaction Protocol)
    async def create_endorse_response(
        self,
        transaction: TransactionRecord,
        state: str,
        use_endorser_did: str = None,
    ):
        """
        Create a response to endorse a transaction.

        Args:
            transaction: The transaction record which would be endorsed.
            state: The state of the transaction record

        Returns:
            The updated transaction and an endorsed response

        """

        if transaction.state not in (
            TransactionRecord.STATE_REQUEST_RECEIVED,
            TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED,
        ):
            raise TransactionManagerError(
                f"Cannot endorse transaction for transaction record"
                f" in state: {transaction.state}"
            )

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE
        transaction_json = transaction.messages_attach[0]["data"]["json"]
        ledger_response = {}

        async with self._profile.session() as session:
            wallet: BaseWallet = session.inject_or(BaseWallet)
            if not wallet:
                raise StorageError("No wallet available")
            endorser_did_info = None
            override_did = (
                use_endorser_did
                if use_endorser_did
                else session.context.settings.get_value(
                    "endorser.endorser_endorse_with_did"
                )
            )
            if override_did:
                endorser_did_info = await wallet.get_local_did(override_did)
            else:
                endorser_did_info = await wallet.get_public_did()
            if not endorser_did_info:
                raise StorageError(
                    "Transaction cannot be endorsed as there is no Public DID in wallet "
                    "or Endorser DID specified"
                )
            endorser_did = endorser_did_info.did
            endorser_verkey = endorser_did_info.verkey

        ledger = self._profile.context.inject_or(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not self._profile.context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise LedgerError(reason=reason)

        async with ledger:
            # check our goal code!
            txn_goal_code = (
                transaction.signature_request[0]["signer_goal_code"]
                if transaction.signature_request
                and "signer_goal_code" in transaction.signature_request[0]
                else TransactionRecord.ENDORSE_TRANSACTION
            )
            if txn_goal_code == TransactionRecord.ENDORSE_TRANSACTION:
                endorsed_msg = await shield(
                    ledger.txn_endorse(transaction_json, endorse_did=endorser_did_info)
                )
            elif txn_goal_code == TransactionRecord.WRITE_DID_TRANSACTION:
                # get DID info from transaction.meta_data
                meta_data = json.loads(transaction_json)
                (success, txn) = await shield(
                    ledger.register_nym(
                        meta_data["did"],
                        meta_data["verkey"],
                        meta_data["alias"],
                        meta_data["role"],
                    )
                )
                # we don't have an endorsed transaction so just return did meta-data
                ledger_response = {
                    "result": {
                        "txn": {"type": "1", "data": {"dest": meta_data["did"]}}
                    },
                    "meta_data": meta_data,
                }
                endorsed_msg = json.dumps(ledger_response)
            else:
                raise TransactionManagerError(
                    f"Invalid goal code for transaction record:" f" {txn_goal_code}"
                )

        # need to return the endorsed msg or else the ledger will reject the
        # eventual transaction write
        transaction.messages_attach[0]["data"]["json"] = endorsed_msg

        signature_response = {
            "message_id": transaction.messages_attach[0]["@id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": txn_goal_code,
            "signature_type": TransactionRecord.SIGNATURE_TYPE,
            "signature": {endorser_did: endorsed_msg or endorser_verkey},
        }

        transaction.signature_response.clear()
        transaction.signature_response.append(signature_response)

        transaction.state = state

        async with self._profile.session() as session:
            await transaction.save(session, reason="Created an endorsed response")

        if (
            transaction.endorser_write_txn
            and txn_goal_code == TransactionRecord.ENDORSE_TRANSACTION
        ):
            # running as the endorser, we've been asked to write the transaction
            ledger_response = await self.complete_transaction(transaction, True)
            endorsed_transaction_response = EndorsedTransactionResponse(
                transaction_id=transaction.thread_id,
                thread_id=transaction._id,
                signature_response=signature_response,
                state=TransactionRecord.STATE_TRANSACTION_ACKED,
                endorser_did=endorser_did,
                ledger_response=ledger_response,
            )

            return transaction, endorsed_transaction_response

        endorsed_transaction_response = EndorsedTransactionResponse(
            transaction_id=transaction.thread_id,
            thread_id=transaction._id,
            signature_response=signature_response,
            state=state,
            endorser_did=endorser_did,
            ledger_response=ledger_response,
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

        # the returned signature is actually the endorsed ledger transaction
        endorser_did = response.endorser_did
        transaction.messages_attach[0]["data"]["json"] = response.signature_response[
            "signature"
        ][endorser_did]

        async with self._profile.session() as session:
            await transaction.save(session, reason="Received an endorsed response")

        # this scenario is where the author has asked the endorser to write the ledger
        if transaction.endorser_write_txn:
            connection_id = transaction.connection_id
            async with self._profile.session() as session:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, connection_id
                )
            await self.endorsed_txn_post_processing(
                transaction, response.ledger_response, connection_record
            )

        return transaction

    async def complete_transaction(
        self, transaction: TransactionRecord, endorser: bool = False
    ):
        """
        Complete a transaction.

        This is the final state where the received ledger transaction
        is written to the ledger.

        Args:
            transaction: The transaction record which would be completed

        Returns:
            The updated transaction

        """

        ledger_transaction = transaction.messages_attach[0]["data"]["json"]

        # check if we (author) have requested the endorser to write the transaction
        if (endorser and transaction.endorser_write_txn) or (
            (not endorser) and (not transaction.endorser_write_txn)
        ):
            ledger = self._profile.inject(BaseLedger)
            if not ledger:
                reason = "No ledger available"
                if not self._profile.context.settings.get_value("wallet.type"):
                    reason += ": missing wallet-type?"
                raise TransactionManagerError(reason)

            async with ledger:
                try:
                    ledger_response_json = await shield(
                        ledger.txn_submit(
                            ledger_transaction, sign=False, taa_accept=False
                        )
                    )
                except (IndyIssuerError, LedgerError) as err:
                    raise TransactionManagerError(err.roll_up) from err

            ledger_response = json.loads(ledger_response_json)

        else:
            ledger_response = ledger_transaction

        transaction.state = TransactionRecord.STATE_TRANSACTION_ACKED

        async with self._profile.session() as session:
            await transaction.save(session, reason="Completed transaction")

        # this scenario is where the endorser is writing the transaction
        # (called from self.create_endorse_response())
        if endorser and transaction.endorser_write_txn:
            return ledger_response

        connection_id = transaction.connection_id
        async with self._profile.session() as session:
            connection_record = await ConnRecord.retrieve_by_id(session, connection_id)
            jobs = await connection_record.metadata_get(session, "transaction_jobs")
        if not jobs:
            raise TransactionManagerError(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        if "transaction_my_job" not in jobs.keys():
            raise TransactionManagerError(
                'The "transaction_my_job" is not set in "transaction_jobs"'
                " in connection metadata for this connection record"
            )
        if jobs["transaction_my_job"] == TransactionJob.TRANSACTION_AUTHOR.name:
            # the author write the endorsed transaction to the ledger
            await self.endorsed_txn_post_processing(
                transaction, ledger_response, connection_record
            )
            transaction_acknowledgement_message = TransactionAcknowledgement(
                thread_id=transaction._id
            )

        elif jobs["transaction_my_job"] == TransactionJob.TRANSACTION_ENDORSER.name:
            transaction_acknowledgement_message = TransactionAcknowledgement(
                thread_id=transaction._id, ledger_response=ledger_response
            )

        return transaction, transaction_acknowledgement_message

    async def receive_transaction_acknowledgement(
        self, response: TransactionAcknowledgement, connection_id: str
    ):
        """
        Update the transaction record after receiving the transaction acknowledgement.

        Args:
            response: The transaction acknowledgement
            connection_id: The connection_id related to this Transaction Record
        """

        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_connection_and_thread(
                session, connection_id, response.thread_id
            )

        if transaction.state != TransactionRecord.STATE_TRANSACTION_ENDORSED:
            raise TransactionManagerError(
                "Only an endorsed transaction can be written to the ledger."
            )

        transaction.state = TransactionRecord.STATE_TRANSACTION_ACKED
        async with self._profile.session() as session:
            await transaction.save(session, reason="Received a transaction ack")

        connection_id = transaction.connection_id

        try:
            async with self._profile.session() as session:
                connection_record = await ConnRecord.retrieve_by_id(
                    session, connection_id
                )
                jobs = await connection_record.metadata_get(session, "transaction_jobs")
        except StorageNotFoundError as err:
            raise TransactionManagerError(err.roll_up) from err
        if not jobs:
            raise TransactionManagerError(
                "The transaction related jobs are not set up in "
                "connection metadata for this connection record"
            )
        if "transaction_my_job" not in jobs.keys():
            raise TransactionManagerError(
                'The "transaction_my_job" is not set in "transaction_jobs"'
                " in connection metadata for this connection record"
            )
        if jobs["transaction_my_job"] == TransactionJob.TRANSACTION_AUTHOR.name:
            # store the related non-secrets record in our wallet
            await self.endorsed_txn_post_processing(
                transaction, response.ledger_response, connection_record
            )

        return transaction

    async def create_refuse_response(
        self, transaction: TransactionRecord, state: str, refuser_did: str
    ):
        """
        Create a response to refuse a transaction.

        Args:
            transaction: The transaction record which would be refused
            state: The state of the transaction record

        Returns:
            The updated transaction and the refused response

        """

        if transaction.state not in (
            TransactionRecord.STATE_REQUEST_RECEIVED,
            TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED,
        ):
            raise TransactionManagerError(
                f"Cannot refuse transaction for transaction record"
                f" in state: {transaction.state}"
            )

        transaction._type = TransactionRecord.SIGNATURE_RESPONSE

        signature_response = {
            "message_id": transaction.messages_attach[0]["@id"],
            "context": TransactionRecord.SIGNATURE_CONTEXT,
            "method": TransactionRecord.ADD_SIGNATURE,
            "signer_goal_code": TransactionRecord.REFUSE_TRANSACTION,
        }
        transaction.signature_response.clear()
        transaction.signature_response.append(signature_response)

        transaction.state = state

        async with self._profile.session() as session:
            await transaction.save(session, reason="Created a refused response")

        refused_transaction_response = RefusedTransactionResponse(
            transaction_id=transaction.thread_id,
            thread_id=transaction._id,
            signature_response=signature_response,
            state=state,
            endorser_did=refuser_did,
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

        async with self._profile.session() as session:
            await transaction.save(session, reason="Received a refused response")

        return transaction

    async def cancel_transaction(self, transaction: TransactionRecord, state: str):
        """
        Cancel a Transaction Request.

        Args:
            transaction: The transaction record which would be cancelled
            state: The state of the transaction record

        Returns:
            The updated transaction and the cancelled transaction response

        """

        if transaction.state not in (
            TransactionRecord.STATE_REQUEST_SENT,
            TransactionRecord.STATE_TRANSACTION_RESENT,
        ):
            raise TransactionManagerError(
                f"Cannot cancel transaction as transaction is"
                f" in state: {transaction.state}"
            )

        transaction.state = state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Cancelled the transaction")

        cancelled_transaction_response = CancelTransaction(
            state=state, thread_id=transaction._id
        )

        return transaction, cancelled_transaction_response

    async def receive_cancel_transaction(
        self, response: CancelTransaction, connection_id: str
    ):
        """
        Update the transaction record to cancel a transaction request.

        Args:
            response: The cancel transaction response
            connection_id: The connection_id related to this Transaction Record
        """

        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_connection_and_thread(
                session, connection_id, response.thread_id
            )

        transaction.state = response.state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Received a cancel request")

        return transaction

    async def transaction_resend(self, transaction: TransactionRecord, state: str):
        """
        Resend a transaction request.

        Args:
            transaction: The transaction record which needs to be resend
            state: the state of the transaction record

        Returns:
            The updated transaction and the resend response

        """

        if transaction.state not in (
            TransactionRecord.STATE_TRANSACTION_REFUSED,
            TransactionRecord.STATE_TRANSACTION_CANCELLED,
        ):
            raise TransactionManagerError(
                f"Cannot resend transaction as transaction is"
                f" in state: {transaction.state}"
            )

        transaction.state = state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Resends the transaction request")

        resend_transaction_response = TransactionResend(
            state=TransactionRecord.STATE_TRANSACTION_RESENT_RECEIEVED,
            thread_id=transaction._id,
        )

        return transaction, resend_transaction_response

    async def receive_transaction_resend(
        self, response: TransactionResend, connection_id: str
    ):
        """
        Update the transaction with a resend request.

        Args:
            response: The Resend transaction response
            connection_id: The connection_id related to this Transaction Record
        """

        async with self._profile.session() as session:
            transaction = await TransactionRecord.retrieve_by_connection_and_thread(
                session, connection_id, response.thread_id
            )

        transaction.state = response.state
        async with self._profile.session() as session:
            await transaction.save(session, reason="Receives a transaction request")

        return transaction

    async def set_transaction_my_job(self, record: ConnRecord, transaction_my_job: str):
        """
        Set transaction_my_job.

        Args:
            record: The connection record in which to set transaction jobs
            transaction_my_job: My transaction job

        Returns:
            The transaction job that is send to other agent

        """

        async with self._profile.session() as session:
            value = await record.metadata_get(session, "transaction_jobs")
            if value:
                value["transaction_my_job"] = transaction_my_job
            else:
                value = {"transaction_my_job": transaction_my_job}
            await record.metadata_set(session, key="transaction_jobs", value=value)

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
            async with self._profile.session() as session:
                connection = await ConnRecord.retrieve_by_did(
                    session, receipt.sender_did, receipt.recipient_did
                )
                value = await connection.metadata_get(session, "transaction_jobs")
                if value:
                    value["transaction_their_job"] = tx_job_received.job
                else:
                    value = {"transaction_their_job": tx_job_received.job}
                await connection.metadata_set(
                    session, key="transaction_jobs", value=value
                )
        except StorageNotFoundError as err:
            raise TransactionManagerError(err.roll_up) from err

    async def endorsed_txn_post_processing(
        self,
        transaction: TransactionRecord,
        ledger_response: dict = None,
        connection_record: ConnRecord = None,
    ):
        """
        Store record in wallet, and kick off any required post-processing.

        Args:
            transaction: The transaction from which the schema/cred_def
                         would be stored in wallet.
        """

        if isinstance(ledger_response, str):
            ledger_response = json.loads(ledger_response)

        ledger = self._profile.inject(BaseLedger)
        if not ledger:
            reason = "No ledger available"
            if not self._profile.context.settings.get_value("wallet.type"):
                reason += ": missing wallet-type?"
            raise TransactionManagerError(reason)

        # setup meta_data to pass to future events, if necessary
        meta_data = transaction.meta_data
        meta_data["endorser"] = {
            "connection_id": transaction.connection_id,
        }

        # write the wallet non-secrets record
        if ledger_response["result"]["txn"]["type"] == "101":
            # schema transaction
            schema_id = ledger_response["result"]["txnMetadata"]["txnId"]
            public_did = ledger_response["result"]["txn"]["metadata"]["from"]
            meta_data["context"]["schema_id"] = schema_id
            meta_data["context"]["public_did"] = public_did

            # Notify schema ledger write event
            await notify_schema_event(self._profile, schema_id, meta_data)

        elif ledger_response["result"]["txn"]["type"] == "102":
            # cred def transaction
            async with ledger:
                try:
                    schema_seq_no = str(ledger_response["result"]["txn"]["data"]["ref"])
                    schema_response = await shield(ledger.get_schema(schema_seq_no))
                except (IndyIssuerError, LedgerError) as err:
                    raise TransactionManagerError(err.roll_up) from err

            schema_id = schema_response["id"]
            cred_def_id = ledger_response["result"]["txnMetadata"]["txnId"]
            issuer_did = ledger_response["result"]["txn"]["metadata"]["from"]
            meta_data["context"]["schema_id"] = schema_id
            meta_data["context"]["cred_def_id"] = cred_def_id
            meta_data["context"]["issuer_did"] = issuer_did

            # Notify event
            await notify_cred_def_event(self._profile, cred_def_id, meta_data)

        elif ledger_response["result"]["txn"]["type"] == "113":
            # revocation registry transaction
            rev_reg_id = ledger_response["result"]["txnMetadata"]["txnId"]
            meta_data["context"]["rev_reg_id"] = rev_reg_id
            await notify_revocation_reg_endorsed_event(
                self._profile, rev_reg_id, meta_data
            )

        elif ledger_response["result"]["txn"]["type"] == "114":
            # revocation entry transaction
            rev_reg_id = ledger_response["result"]["txn"]["data"]["revocRegDefId"]
            meta_data["context"]["rev_reg_id"] = rev_reg_id
            await notify_revocation_entry_endorsed_event(
                self._profile, rev_reg_id, meta_data
            )

        elif ledger_response["result"]["txn"]["type"] == "1":
            # write DID to ledger
            did = ledger_response["result"]["txn"]["data"]["dest"]
            await notify_endorse_did_event(self._profile, did, meta_data)

        elif ledger_response["result"]["txn"]["type"] == "100":
            # write DID ATTRIB to ledger
            did = ledger_response["result"]["txn"]["data"]["dest"]
            await notify_endorse_did_attrib_event(self._profile, did, meta_data)

        else:
            # TODO unknown ledger transaction type, just ignore for now ...
            pass
