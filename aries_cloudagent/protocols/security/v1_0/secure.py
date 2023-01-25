import hashlib
import hmac


def sign_secret(secret_key, payload):
    return hmac.new(
        secret_key.encode("utf-8"),
        str(payload).encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
