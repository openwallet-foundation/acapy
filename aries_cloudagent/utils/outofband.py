"""Utilities for creating out-of-band messages."""

import json

from urllib.parse import quote, urljoin

from ..config.injection_context import InjectionContext
from ..messaging.agent_message import AgentMessage
from ..wallet.base import DIDInfo
from ..wallet.util import bytes_to_b64


def serialize_outofband(
    context: InjectionContext, message: AgentMessage, did: DIDInfo, endpoint: str
) -> str:
    """
    Serialize the agent message as an out-of-band message.

    Returns:
        An OOB message in URL format.

    """
    body = message.serialize()
    # FIXME no support for routing keys
    body["~service"] = {
        "recipientKeys": [did.verkey],
        "routingKeys": [],
        "serviceEndpoint": endpoint,
    }
    d_m = quote(bytes_to_b64(json.dumps(body).encode("ascii")))
    result = urljoin(endpoint, "?d_m={}".format(d_m))
    return result
