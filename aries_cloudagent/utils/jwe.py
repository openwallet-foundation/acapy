"""JSON Web Encryption utility methods."""

from aries_cloudagent.core.error import BaseError
from typing import List

import json
from base64 import b64decode


class RecipientKeysError(BaseError):
    """Error raised when extracting recipient keys from JWE fails."""


def get_recipient_keys(jwe: dict) -> List[str]:
    """Get all recipient kid headers from a jwe message

    Args:
        jwe: json web encryption message

    Returns:
        List of recipient keys for the jwe
    """

    try:
        protected = json.loads(b64decode(jwe["protected"]))
        recipients = protected["recipients"]

        recipient_keys = [recipient["header"]["kid"] for recipient in recipients]
    except Exception as e:
        raise RecipientKeysError("Error trying to extract recipient keys from JWE", e)

    return recipient_keys
