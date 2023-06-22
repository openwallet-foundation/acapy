import logging

from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.wallet.key_type import ED25519

LOGGER = logging.getLogger(__name__)


def add_jwt_headers(headers, verification_method):
    headers["alg"] = "EdDSA"
    headers["typ"] = "JWT"
    headers["kid"] = verification_method
    return None


async def jwt_sign(context, encoded_headers, encoded_payload, did):
    """ """
    async with context.session() as session:
        wallet = session.inject(BaseWallet)
        LOGGER.info(f"jwt sign: {did}")
        did_info = await wallet.get_local_did(did)
        return await wallet.sign_message(
            f"{encoded_headers}.{encoded_payload}".encode(), did_info.verkey
        )


async def jwt_verify(
    context, encoded_header, encoded_payload, decoded_signature, verkey
):
    async with context.session() as session:
        wallet = session.inject(BaseWallet)
        return await wallet.verify_message(
            f"{encoded_header}.{encoded_payload}", decoded_signature, verkey, ED25519
        )
