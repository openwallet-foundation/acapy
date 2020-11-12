from aiohttp import web
from aiohttp_apispec import request_schema, docs, response_schema, querystring_schema, match_info_schema
from marshmallow import fields
from ....utils.tracing import AdminAPIMessageTracingSchema
from .manager import TransactionManager
from .transaction_record import TransactionRecord, TransactionRecordSchema
from ....connections.models.connection_record import ConnectionRecord

from .messages.transaction_request import TransactionRequest
from .messages.transaction_response import TransactionResponse
from .messages.cancel_transaction import CancelTransaction
from .messages.transaction_resend import TransactionResend

from ....messaging.models.openapi import OpenAPISchema

from ....messaging.valid import UUIDFour





class TransactionListSchema(OpenAPISchema):
    """Result schema for connection list."""

    results = fields.List(
        fields.Nested(TransactionRecordSchema()),
        description="List of transaction records",
    )


class TransactionsListQueryStringSchema(OpenAPISchema):

    comment1 = fields.Str(
        required=False,
        example="comment1"
    )
    comment2 = fields.Str(
        required=False,
        example="comment2"
    )


class TranIdMatchInfoSchema(OpenAPISchema):
    """Path parameters and validators for request taking connection id."""

    tran_id = fields.Str(
        description="Transaction identifier", required=True, example=UUIDFour.EXAMPLE
    )

class CreateTransactionRecordSchema(AdminAPIMessageTracingSchema):

    comment1 = fields.Str(
        description="Some comment",
        required=False,
        )

    comment2 = fields.Str(
        description="Some comment",
        required=False,
        )

    conn_id = fields.Str(
        description="Connection identifier", required=True, example="some"
    )

    attr_names = fields.List(
        fields.Str(example = "color"), description="Alist of attributes for this Schema", required=True
    )

    name = fields.Str(
        description="The name of the schema", required=True, example="Schema"
    )

    version = fields.Str(
        description="The verion of this schema", required=True, example="1.0"
    )



@docs(
    tags=["endorse-transaction"],
    summary="Query transactions",
)
@querystring_schema(TransactionsListQueryStringSchema())
@response_schema(TransactionListSchema(), 200)
async def transactions_list(request: web.BaseRequest):

    context = request.app["request_context"]

    tag_filter = {}
    post_filter = {}
    
    """
    for param_name in (
        "comment1"
    ):
        if param_name in request.query and request.query[param_name] != "":
            tag_filter[param_name] = request.query[param_name]

    
    for param_name in (
        "comment2"
    ):
        if param_name in request.query and request.query[param_name] != "":
            post_filter[param_name] = request.query[param_name]
    """
    
    
    records = await TransactionRecord.query(context, tag_filter, post_filter)
    results = [record.serialize() for record in records]

    return web.json_response({"results": results})




@docs(tags=["endorse-transaction"], summary="Fetch a single transaction record")
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transactions_retrieve(request: web.BaseRequest):

    context = request.app["request_context"]
    transaction_id = request.match_info["tran_id"]

    record = await TransactionRecord.retrieve_by_id(context, transaction_id)
    result = record.serialize()

    return web.json_response(result)


@docs(
    tags=["endorse-transaction"],
    summary="Send a transaction request",
)
@request_schema(CreateTransactionRecordSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_record_create(request: web.BaseRequest):

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    body = await request.json()
    
    comment1 = body.get("comment1")
    comment2 = body.get("comment2")
    connection_id = body.get("conn_id")
    attr_names = body.get("attr_names")
    name = body.get("name")
    version = body.get("version")


    connection = await ConnectionRecord.retrieve_by_id(context, connection_id)

    created_transaction_request = TransactionRequest(comment1=comment1, comment2=comment2, attr_names=attr_names, name=name, version=version)

    print("Test In transaction record create 1")
    print(created_transaction_request._id)
    print(created_transaction_request._thread_id)
    transaction_mgr = TransactionManager(context)
    transaction = await transaction_mgr.create_request(comment1=comment1, 
                                                        comment2=comment2, 
                                                        attr_names=attr_names, 
                                                        name=name, 
                                                        version=version, 
                                                        thread_id=created_transaction_request._thread_id,
                                                        connection_id=connection_id,
                                                        )

    await outbound_handler(created_transaction_request, connection_id=connection.connection_id)

    return web.json_response(transaction.serialize()) 




@docs(tags=["endorse-transaction"], summary="Create a response for a particular transaction record")
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_create_response(request: web.BaseRequest):

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]

    transaction_mgr = TransactionManager(context)

    transaction = await TransactionRecord.retrieve_by_id(context, transaction_id)
    transaction = await transaction_mgr.create_response(transaction=transaction, state="Responded")

    created_transaction_response = TransactionResponse(state="Responded", thread_id=transaction.thread_id)
    await outbound_handler(created_transaction_response, connection_id=transaction.connection_id)

    return web.json_response(transaction.serialize()) 





@docs(tags=["endorse-transaction"], summary="Cancel a particular transaction record")
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def cancel_transaction(request:web.BaseRequest):

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]

    transaction_mgr = TransactionManager(context)

    transaction = await TransactionRecord.retrieve_by_id(context, transaction_id)
    transaction = await transaction_mgr.cancel_transaction(transaction=transaction, state="CANCELLED")

    created_transaction_cancel = CancelTransaction(state="CANCELLED", thread_id=transaction.thread_id)
    await outbound_handler(created_transaction_cancel, connection_id=transaction.connection_id)

    return web.json_response(transaction.serialize()) 




@docs(tags=["endorse-transaction"], summary="Resend a particular transaction record")
@match_info_schema(TranIdMatchInfoSchema())
@response_schema(TransactionRecordSchema(), 200)
async def transaction_resend(request:web.BaseRequest):

    context = request.app["request_context"]
    outbound_handler = request.app["outbound_message_router"]

    transaction_id = request.match_info["tran_id"]

    transaction_mgr = TransactionManager(context)

    transaction = await TransactionRecord.retrieve_by_id(context, transaction_id)
    transaction = await transaction_mgr.transaction_resend(transaction=transaction, state="RESEND")

    created_transaction_resend = TransactionResend(state="RESEND",thread_id=transaction.thread_id)
    await outbound_handler(created_transaction_resend, connection_id=transaction.connection_id)


    return web.json_response(transaction.serialize()) 



    




async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/transactions", transactions_list, allow_head=False),
            web.get("/transactions/{tran_id}", transactions_retrieve, allow_head=False),
            web.post("/transactions/create-endorse-request", transaction_record_create),
            web.post("/transactions/{tran_id}/create-response", transaction_create_response),
            web.post("/transactions/{tran_id}/cancel", cancel_transaction),
            web.post("/transaction/{tran_id}/resend", transaction_resend)
        ]
    )

def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "endorse-transaction",
            "description": "Endorse a Transaction",
        }
    )

