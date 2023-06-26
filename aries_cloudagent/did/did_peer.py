"""DID Peer class and resolver methods."""
import json

from enum import Enum
from typing import Union, Optional
from io import BytesIO
from peerdid import dids, keys

from ..connections.models.diddoc import DIDDoc, DIDPeerDoc
from ..messaging.valid import PeerDID
from ..wallet.util import multi_hash_encode, multi_base_encode


class PeerDidNumAlgo(Enum):
    INCEPTION_KEY_WITHOUT_DOC = 0
    GENESIS_DOC = 1
    MULTIPLE_INCEPTION_KEY_WITHOUT_DOC = 2


def get_did_from_did_doc(did_doc: Union[DIDDoc, DIDPeerDoc]) -> str:
    #use lib functions
    pass

def is_valid_peer_did(did: str) -> bool:
    return bool(PeerDID.PATTERN.match(did))


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
    
    

def create_peer_did_2(verkey: bytes, service: dict) -> "DIDPeerDoc":

    enc_keys = [keys.X25519KeyAgreementKey(verkey)]
    sign_keys = [keys.Ed25519VerificationKey(verkey)]

    service = {
        "type": "DIDCommMessaging",
        "serviceEndpoint": "https://example.com/endpoint1",
        "routingKeys": ["did:example:somemediator#somekey1"],
        "accept": ["didcomm/v2", "didcomm/aip2;env=rfc587"],
    }

    var = dids.create_peer_did_numalgo_2(enc_keys, sign_keys,service)
    print(var)

