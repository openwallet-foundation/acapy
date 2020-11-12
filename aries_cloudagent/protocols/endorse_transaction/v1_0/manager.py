from ....config.injection_context import InjectionContext
from aiohttp import web
import logging
from .transaction_record import TransactionRecord
from .messages.transaction_request import TransactionRequest
from .messages.transaction_response import TransactionResponse
from .messages.cancel_transaction import CancelTransaction
from .messages.transaction_resend import TransactionResend
from .messages.messages_attach import MessagesAttach

from ....wallet.base import BaseWallet


SIGNATURE_REQUEST = "http://didcomm.org/sign-attachment/%VER/signature-request"

SIGNATURE_TYPE = "<requested signature type>"

SIGNATURE_CONTEXT = "did:sov"

ADD_SIGNATURE = "add-signature"

ENDORSE_TRANSACTION = "transaction.endorse"
REFUSE_TRANSACTION = "transaction.refuse"
WRITE_TRANSACTION = "transaction.ledger.write"

FORMAT_VERSION = "<format-and-version>"


class TransactionManager:

    def __init__(self, context: InjectionContext):
        """
        Initialize a TransactionManager.

        Args:
            context: The context for this connection manager
        """
        self._context = context
        self._logger = logging.getLogger(__name__)

    
    @property
    def context(self):
        """
        Accessor for the current injection context.

        Returns:
            The injection context for this connection manager

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
                            request: web.BaseRequest = None
                            ):


        #messages_attach = MessagesAttach(author_did="V4SGRU86Z58d6TV7PBUe6f", endorser_did="LjgpST2rjsoxYegQDRm7EL", attr_names=attr_names, name=name, version=version)

        
        transaction = TransactionRecord(comment1=comment1, comment2=comment2)

        #transaction._type = SIGNATURE_REQUEST

        """
        signature_request = {
            "context":SIGNATURE_CONTEXT,
            "method":ADD_SIGNATURE,
            "signature_type" : SIGNATURE_TYPE,
            "signer_goal_code" : ENDORSE_TRANSACTION,
            "author_goal_code" : WRITE_TRANSACTION
        }
        """

        #transaction.signature_request.append(signature_request)

        """
        formats = {
            "attach_id" : messages_attach._id,
            "format": FORMAT_VERSION
        }
        """

        #transaction.formats.append(formats)
        #transaction.messages_attach.append(messages_attach)   








        await transaction.create_transaction_request(attr_names=attr_names, name=name, version=version)
        transaction.thread_id = thread_id
        transaction.connection_id = connection_id

        await transaction.save(self.context, reason="Created transaction request")

        return transaction


    async def receive_request(self, request:TransactionRequest):

            connection_id = self.context.connection_record.connection_id
            transaction = TransactionRecord(comment1=request.comment1, comment2=request.comment2)
            await transaction.receive_transaction_request(attr_names=request.attr_names, name=request.name, version=request.version)
            transaction.thread_id = request._thread_id
            transaction.connection_id = connection_id
            
            await transaction.save(self.context, reason="Received transaction request")

            #test_transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, request._thread_id)


   
    
    
    
    async def create_response(self, transaction:TransactionRecord = None, state:str = None):

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        return transaction



    async def receive_response(self, response:TransactionResponse):

        connection_id = self.context.connection_record.connection_id
        transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, response.thread_id)

        transaction.state = response.state
        await transaction.save(self.context, reason="Updates Transaction record")

    
    
    
    
    async def cancel_transaction(self, transaction:TransactionRecord = None, state:str = None):

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        return transaction

    async def receive_cancel_transaction(self, response:CancelTransaction):

        connection_id = self.context.connection_record.connection_id
        transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, response.thread_id)

        transaction.state = response.state
        await transaction.save(self.context, reason="Updates Transaction record")




    async def transaction_resend(self, transaction:TransactionRecord = None, state:str = None):

        transaction.state = state
        await transaction.save(self.context, reason="Updates Transaction record")

        return transaction

    
    async def receive_transaction_resend(self, response:TransactionResend):

        connection_id = self.context.connection_record.connection_id
        transaction = await TransactionRecord.retrieve_by_connection_and_thread(self.context, connection_id, response.thread_id)

        transaction.state = response.state
        await transaction.save(self.context, reason="Updates Transaction record")



        
