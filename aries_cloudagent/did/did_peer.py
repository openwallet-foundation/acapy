"""DID Peer class and resolver methods."""
import json

from enum import Enum
from typing import Union, Optional
from io import BytesIO

from ..connections.models.diddoc import DIDDoc, DIDPeerDoc
from ..messaging.valid import PeerDID
from ..wallet.util import multi_hash_encode, multi_base_encode


class PeerDidNumAlgo(Enum):
    INCEPTION_KEY_WITHOUT_DOC = 0
    GENESIS_DOC = 1
    MULTIPLE_INCEPTION_KEY_WITHOUT_DOC = 2


def get_did_from_did_doc(did_doc: Union[DIDDoc, DIDPeerDoc]) -> str:
    did_doc_dict = did_doc.serialize()
    del did_doc_dict["id"]
    did_doc_json = json.dumps(did_doc_dict)
    did_doc_json_buffer = BytesIO(did_doc_json.encode("utf-8"))
    enc_num_basis = multi_base_encode(
        multi_hash_encode(did_doc_json_buffer, "sha2-256")
    )
    return f"did:peer:1{enc_num_basis}"


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
