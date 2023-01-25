from aiohttp import web
from aiohttp_apispec import docs
import json
import jwt
from ....admin.request_context import AdminRequestContext
from ....multitenant.base import BaseMultitenantManager


@docs(tags=["security"], summary="To provide authentication to ACA-py lib")
async def secret_key_receiver(request: web.BaseRequest) -> json:
    try:
        context: AdminRequestContext = request["context"]
        secret_key = {"secret_key": request.match_info["webhook_secret"]}
        request_token = request.headers["Authorization"].split(" ")[1]
        decoded_token = jwt.decode(request_token, options={"verify_signature": False})
        multitenant_mgr = context.profile.inject(BaseMultitenantManager)
        wallet_record = await multitenant_mgr.update_wallet(
            decoded_token["wallet_id"], secret_key
        )
        return web.json_response({"message": "Secret Key received successfully"})
    except Exception as e:
        return web.json_response({"error Message": str(e)})


async def register(app: web.Application):
    """Register routes"""
    app.add_routes([web.post("/secret-key/{webhook_secret}", secret_key_receiver)])


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {"name": "security", "description": "testing security"}
    )
