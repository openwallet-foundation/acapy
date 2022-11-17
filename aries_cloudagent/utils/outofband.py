"""Utilities for creating out-of-band messages."""

import json

from urllib.parse import quote, urljoin

from ..messaging.agent_message import AgentMessage
from ..wallet.did_info import DIDInfo
from ..wallet.util import str_to_b64


def serialize_outofband(message: AgentMessage, did: DIDInfo, endpoint: str) -> str:
    """
    Serialize the agent message as an out-of-band message.

    Returns:
        An OOB message in URL format.

    """
    body = message.serialize()
    # FIXME no support for routing keys
    body["~services"] = {
        "recipientKeys": [did.verkey],
        "routingKeys": [],
        "serviceEndpoint": endpoint,
    }
    d_m = quote(str_to_b64(json.dumps(body)))
    return urljoin(endpoint, "?d_m={}".format(d_m))
