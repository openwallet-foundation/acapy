
from ....config.injection_context import InjectionContext
from aiohttp import web
import logging

from .transaction_record import TransactionRecord
from .messages.transaction_request import TransactionRequest
from .messages.endorsed_transaction_response import EndorsedTransactionResponse
from .messages.refused_transaction_response import RefusedTransactionResponse
from .messages.cancel_transaction import CancelTransaction
from .messages.transaction_resend import TransactionResend
from .messages.messages_attach import MessagesAttach

from ....ledger.base import BaseLedger
from ....ledger.error import LedgerError

from ....wallet.base import BaseWallet


SIGNATURE_REQUEST = "http://didcomm.org/sign-attachment/%VER/signature-request"

SIGNATURE_RESPONSE = "http://didcomm.org/sign-attachment/%VER/signature-response"

SIGNATURE_TYPE = "<requested signature type>"

SIGNATURE_CONTEXT = "did:sov"

ADD_SIGNATURE = "add-signature"

ENDORSE_TRANSACTION = "transaction.endorse"
REFUSE_TRANSACTION = "transaction.refuse"
WRITE_TRANSACTION = "transaction.ledger.write"

FORMAT_VERSION = "dif/endorse-transaction/request@v1.0"


class TransactionManager:

    def __init__(self, context: InjectionContext):
        """
        Initialize a TransactionManager.

        Args:
            context: The context for this transaction manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    
    @property
    def context(self):
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this transaction manager

        """
        return self._context


    async def create_request(
                            self, 
                            comment1:str = None, 
                            comment2:str = None, 
                            attr_names:list = [], 
                            name:str = None, 
                            version:str = None, 
                            thread_id:str = None, 
                            connection_id:str = None,
                            expires_time:str = None,
                            request: web.BaseRequest = None
                            ):
        
        wallet: BaseWallet = await self.context.inject(BaseWallet, required=False)
        author_did_info = await wallet.get_public_did()
        author_did = author_did_info.did
        author_verkey = author_did_info.verkey

        ledger: BaseLedger = await self.context.inject(BaseLedger, required=False)

        if not ledger or ledger.type != "indy":
            reason = "No indy ledger available"
            if not self.context.settings.get_value("wallet.type"):
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
        
        if taa_info["taa_accepted"] != None:
            mechanism = taa_info["taa_accepted"]["mechanism"]
            time = taa_info["taa_accepted"]["time"]
        else:
            mechanism = None
            time = None

        if taa_info["taa_record"] != None:
            taaDigest = taa_info["taa_record"]["digest"]
        else:
            taaDigest = None

        messages_attach = MessagesAttach(
                                        author_did=author_did,
                                        author_verkey=author_verkey, 
                                        attr_names=attr_names, 
                                        name=name, 
                                        version=version,
                                        mechanism=mechanism,
                                        taaDigest=taaDigest,
                                        time=time
                                        )
        messages_attach_dict = messages_attach.__dict__        
        
        transaction = TransactionRecord(comment1=comment1, comment2=comment2)
        transaction._type = SIGNATURE_REQUEST
        
        signature_request = {
            "context":SIGNATURE_CONTEXT,
            "method":ADD_SIGNATURE,
            "signature_type" : SIGNATURE_TYPE,
            "signer_goal_code" : ENDORSE_TRANSACTION,
            "author_goal_code" : WRITE_TRANSACTION
        }
        transaction.signature_request.append(signature_request)

        timing = {
            "expires_time": "1597708800"
        }
        transaction.timing = timing
        
        formats = {
            "attach_id" : messages_attach._id,
            "format": FORMAT_VERSION
        }
        transaction.formats.append(formats)

        transaction.messages_attach.append(messages_attach_dict)
        transaction.connection_id = connection_id

        await transaction.save(self.context, reason="Created transaction request")

        transaction_request = TransactionRequest(
                                                transaction_id=transaction._id, 
                                                signature_request=signature_request, 
                                                messages_attach=messages_attach_dict,
                                                timing=timing
                                                )

        return transaction, transaction_request
        

    async def receive_request(self, request:TransactionRequest):

            connection_id = self.context.connection_record.connection_id
            transaction = TransactionRecord(comment1=request.comment1, comment2=request.comment2)

            transaction._type = SIGNATURE_REQUEST
            transaction.signature_request.append(request.signature_request)
            transaction.timing = request.timing

            format = {
                "attach_id" : request.messages_attach["_message_id"],
                "format": FORMAT_VERSION
            }
            transaction.formats.append(format)

            transaction.messages_attach.append(request.messages_attach)
            transaction.thread_id = request.transaction_id
            transaction.connection_id = connection_id
            
            await transaction.save(self.context, reason="Received transaction request")    
    
    
    async def create_endorse_response(self, transaction:TransactionRecord = None, state:str = None):

        wallet: BaseWallet = await self.context.inject(BaseWallet, required=False) 
        endorser_did_info = await wallet.get_public_did()
        endorser_did = endorser_did_info.did
        endorser_verkey = endorser_did_info.verkey

        transaction.messages_attach[0]["data"]["json"]["endorser"] = endorser_did

        transaction._type = SIGNATURE_RESPONSE
        
        signature_response = {
            "message_id" : transaction.messages_attach[0]["_message_id"],
            "context" : SIGNATURE_CONTEXT,
            "method" : ADD_SIGNATURE,
            "signer_goal_code" : ENDORSE_TRANSACTION,
            "signature_type" : SIGNATURE_TYPE,
            "signature" : {
                endorser_did : endorser_verkey
            }
        }
        transaction.signature_response.append(signature_response)

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        endorsed_transaction_response = EndorsedTransactionResponse(
                                                                    transaction_id = transaction.thread_id,
                                                                    thread_id = transaction._id,
                                                                    signature_response = signature_response,
                                                                    state = state, 
                                                                    endorser_did=endorser_did
                                                                    )

        return transaction, endorsed_transaction_response


    async def receive_endorse_response(self, response:EndorsedTransactionResponse):

        transaction = await TransactionRecord.retrieve_by_id(self.context, response.transaction_id)

        transaction._type = SIGNATURE_RESPONSE        
        transaction.state = response.state

        transaction.signature_response.append(response.signature_response)

        transaction.thread_id = response.thread_id
        transaction.messages_attach[0]["data"]["json"]["endorser"] = response.endorser_did

        await transaction.save(self.context, reason="Updates Transaction record")


    async def create_refuse_response(self, transaction:TransactionRecord = None, state:str = None):

        wallet: BaseWallet = await self.context.inject(BaseWallet, required=False)
        endorser_did = await wallet.get_public_did()
        endorser_did = endorser_did.did

        transaction.messages_attach[0]["data"]["json"]["endorser"] = endorser_did

        transaction._type = SIGNATURE_RESPONSE
        
        signature_response = {
            "message_id" : transaction.messages_attach[0]["_message_id"],
            "context" : SIGNATURE_CONTEXT,
            "method" : ADD_SIGNATURE,
            "signer_goal_code" : REFUSE_TRANSACTION
        }
        transaction.signature_response.append(signature_response)

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        refused_transaction_response = RefusedTransactionResponse(
                                                                    transaction_id = transaction.thread_id,
                                                                    thread_id = transaction._id,
                                                                    signature_response = signature_response,
                                                                    state = state,
                                                                    endorser_did=endorser_did
                                                                    )

        return transaction, refused_transaction_response


    async def receive_refuse_response(self, response:RefusedTransactionResponse):

        transaction = await TransactionRecord.retrieve_by_id(self.context, response.transaction_id)

        transaction._type = SIGNATURE_RESPONSE        
        transaction.state = response.state

        transaction.signature_response.append(response.signature_response)
        transaction.thread_id = response.thread_id
        transaction.messages_attach[0]["data"]["json"]["endorser"] = response.endorser_did

        await transaction.save(self.context, reason="Updates Transaction record")    
    
    
    async def cancel_transaction(self, transaction:TransactionRecord = None, state:str = None):

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        cancelled_transaction_response = CancelTransaction(state="CANCELLED", thread_id=transaction._id)

        return transaction, cancelled_transaction_response


    async def receive_cancel_transaction(self, response:CancelTransaction):

        connection_id = self.context.connection_record.connection_id
        transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, response.thread_id)

        transaction.state = response.state
        await transaction.save(self.context, reason="Updates Transaction record")


    async def transaction_resend(self, transaction:TransactionRecord = None, state:str = None):

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        resend_transaction_response = TransactionResend(state="RESEND", thread_id=transaction._id)

        return transaction, resend_transaction_response

    
    async def receive_transaction_resend(self, response:TransactionResend):

        connection_id = self.context.connection_record.connection_id
        transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, response.thread_id)

        transaction.state = response.state
        await transaction.save(self.context, reason="Updates Transaction record")        
