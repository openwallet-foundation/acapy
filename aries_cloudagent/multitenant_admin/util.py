"""Multitenant Admin util."""

import jwt

from ..wallet.models.wallet_record import WalletRecord


# MTODO: move to better place
def get_wallet_jwt(context, wallet_record: WalletRecord, wallet_key: str = None) -> str:
    """Get JWT based on wallet record and context."""

    jwt_secret = context.settings.get("multitenant.jwt_secret")

    payload = {"wallet_id": wallet_record.wallet_record_id}

    if wallet_record.key_management_mode == WalletRecord.MODE_UNMANAGED:
        # MTODO: maybe check if wallet_key is provided?
        payload["wallet_key"] = wallet_key

    jwt_bytes = jwt.encode(payload, jwt_secret)
    jwt_string = jwt_bytes.decode()

    return jwt_string
