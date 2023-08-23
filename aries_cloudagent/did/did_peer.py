"""DID Peer class and resolver methods."""

from enum import Enum
from typing import Union, Optional


DID_COMM_V1_SERVICE_TYPE = "did-communication"

class PeerDidNumAlgo(Enum):
    INCEPTION_KEY_WITHOUT_DOC = 0
    GENESIS_DOC = 1
    MULTIPLE_INCEPTION_KEY_WITHOUT_DOC = 2



def get_num_algo_from_peer_did(did: str) -> Optional[PeerDidNumAlgo]:
    num_algo = did[9]
    if num_algo == PeerDidNumAlgo.INCEPTION_KEY_WITHOUT_DOC:
        return PeerDidNumAlgo.INCEPTION_KEY_WITHOUT_DOC
    elif num_algo == PeerDidNumAlgo.GENESIS_DOC:
        return PeerDidNumAlgo.GENESIS_DOC
    elif num_algo == PeerDidNumAlgo.MULTIPLE_INCEPTION_KEY_WITHOUT_DOC:
        return PeerDidNumAlgo.MULTIPLE_INCEPTION_KEY_WITHOUT_DOC
    else:
        return None

