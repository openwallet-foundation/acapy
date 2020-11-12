
from marshmallow import fields
from ....messaging.models.base_record import BaseRecord, BaseRecordSchema, BaseExchangeRecord, BaseExchangeSchema
from ....config.injection_context import InjectionContext

class TransactionRecord(BaseExchangeRecord):

    class Meta:

        schema_class = "TransactionRecordSchema"

    
    RECORD_ID_NAME = "transaction_id"
    TAG_NAMES = {"comment1", "comment2", "state", "thread_id", "connection_id"}    
    RECORD_TYPE = "transaction"
    STATE_INIT = "init"

    
    def __init__(
        self,
        *,
        transaction_id: str = None,
        comment1: str = None,
        comment2: str = None,
        # MAIN OBJECT STARTED 
        _type: str = None,
        comment: str = None,
        signature_request: list = [],
        timing: dict = {},
        formats: list = [],
        messages_attach: list = [],

        thread_id:str = None,
        connection_id:str = None,

        state: str = None,
        **kwargs,
    ):

        super().__init__(transaction_id, state or self.STATE_INIT, **kwargs)
        self.comment1 = comment1
        self.comment2 = comment2

        # MAIN OBJECT STARTED
        self._type = _type
        self.comment = comment
        self.signature_request = signature_request
        self.timing = timing
        self.formats = formats
        self.messages_attach = messages_attach

        self.thread_id = thread_id
        self.connection_id = connection_id


        #self.state = state



    
    # Experimental Feature  # Will need to change it

    @classmethod
    async def retrieve_by_connection_and_thread(
        cls, context: InjectionContext, connection_id: str, thread_id: str
    ) -> "TransactionRecord":
        """Retrieve a credential exchange record by connection and thread ID."""
        cache_key = f"credential_exchange_ctidx::{connection_id}::{thread_id}"
        record_id = await cls.get_cached_key(context, cache_key)
        if record_id:
            record = await cls.retrieve_by_id(context, record_id)
        else:
            record = await cls.retrieve_by_tag_filter(
                context,
                {"thread_id": thread_id},
                {"connection_id": connection_id} if connection_id else None,
            )
            await cls.set_cached_key(context, cache_key, record._id)
        return record









    
    
    
    
    
    
    
    
    
    
    
    async def create_transaction_request(self, attr_names:list, name:str, version:str):



        self._type = "http://didcomm.org/sign-attachment/%VER/signature-request"

        sign_request = {
            "context": "did:sov",
            "method": "add-signature",
            "signature_type": "<requested signature type>",
            "signer_goal_code": "transaction.endorse",
            "author_goal_code": "ledger.transaction.write"
        }

        self.signature_request.append(sign_request)

        self.timing = {"expires_time": "2020-12-13T17:29:06+0000"}

        form = {
            "attach_id" : "<attach@id value>",
            "format" : "<format-and-version>"
            }

        self.formats.append(form)

        msg_attach = {
            "@id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
            "mime-type": "application/json",
            "data": {
            "json": {
                "endorser": "V4SGRU86Z58d6TV7PBUe6f",
                "identifier": "LjgpST2rjsoxYegQDRm7EL",
                "operation": {
                "data": {
                    "attr_names": attr_names,
                    "name": name,
                    "version": version
                },
                "type": "101"
                },
                "protocolVersion": 2,
                "reqId": 1597766666168851000,
                "signatures": {
                "LjgpST2rjsoxYegQDRm7EL": "4uq1mUATKMn6Y9sTgwqaGWGTTsYm7py2c2M8x1EVDTWKZArwyuPgjUEw5UBysWNbkf2SN6SqVwbfSqCfnbm1Vnfw"
                },
                "taaAcceptance": { 
                "mechanism": "manual",
                "taaDigest": "f50feca75664270842bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62",
                "time": 1597708800
                }
            }
            }
        }

        self.messages_attach.append(msg_attach)

    
    
    async def receive_transaction_request(self, attr_names:list, name:str, version:str):


        self._type = "http://didcomm.org/sign-attachment/%VER/signature-request"

        sign_request = {
            "context": "did:sov",
            "method": "add-signature",
            "signature_type": "<requested signature type>",
            "signer_goal_code": "transaction.endorse",
            "author_goal_code": "ledger.transaction.write"
        }

        self.signature_request.append(sign_request)

        self.timing = {"expires_time": "2020-12-13T17:29:06+0000"}

        form = {
            "attach_id" : "<attach@id value>",
            "format" : "<format-and-version>"
            }

        self.formats.append(form)

        msg_attach = {
            "@id": "143c458d-1b1c-40c7-ab85-4d16808ddf0a",
            "mime-type": "application/json",
            "data": {
            "json": {
                "endorser": "V4SGRU86Z58d6TV7PBUe6f",
                "identifier": "LjgpST2rjsoxYegQDRm7EL",
                "operation": {
                "data": {
                    "attr_names": attr_names,
                    "name": name,
                    "version": version
                },
                "type": "101"
                },
                "protocolVersion": 2,
                "reqId": 1597766666168851000,
                "signatures": {
                "LjgpST2rjsoxYegQDRm7EL": "4uq1mUATKMn6Y9sTgwqaGWGTTsYm7py2c2M8x1EVDTWKZArwyuPgjUEw5UBysWNbkf2SN6SqVwbfSqCfnbm1Vnfw"
                },
                "taaAcceptance": { 
                "mechanism": "manual",
                "taaDigest": "f50feca75664270842bd4202c2ab977006761d36bd6f23e4c6a7e0fc2feb9f62",
                "time": 1597708800
                }
            }
            }
        }

        self.messages_attach.append(msg_attach)

    
        



class TransactionRecordSchema(BaseExchangeSchema):

    class Meta:

        model_class = "TransactionRecord"

    """
    transaction_id = fields.Str(
        required=False, description="Connection identifier", example="any_example"
    )
    """

    _id = fields.Str(
        required=False, description="Connection identifier", example="any_example"
    )

    comment1 = fields.Str(
        required=False,
        description="Some comment",
        example="Some Comment",
    )

    comment2 = fields.Str(
        required=False,
        description="Some comment",
        example="Some Comment",
    )

    _type = fields.Str(
        required=False, description="Transaction type", example="The type of transaction"
    )

    signature_request = fields.List(
        fields.Dict(),
        required=False,
    )

    timing = fields.Dict(
        required=False
    )

    formats = fields.List(
        fields.Dict(),
        required=False
    )

    messages_attach = fields.List(
        fields.Dict(),
        required=False
    )

    thread_id = fields.Str(
        required=False,
        description="Thread Identifier"
    )

    connection_id = fields.Str(
        required=False,
        description="The connection identifier for thie particular transaction record"
    )









