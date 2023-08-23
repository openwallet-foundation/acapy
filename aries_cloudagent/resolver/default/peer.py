"""Key DID Resolver.

Resolution is performed using the IndyLedger class.
"""

import re
from hashlib import sha256
from typing import Optional, Pattern, Sequence, Text, Union, Tuple, Dict, List

from peerdid.dids import is_peer_did, PEER_DID_PATTERN, resolve_peer_did, DID, MalformedPeerDIDError, DIDDocument, DIDUrl
from peerdid.keys import to_multibase, MultibaseFormat

from ...connections.base_manager import BaseConnectionManager

from ...config.injection_context import InjectionContext
from ...core.profile import Profile
from ...messaging.valid import DIDKey as DIDKeyType

from ..base import BaseDIDResolver, DIDNotFound, ResolverType


class PeerDID2Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return PEER_DID_PATTERN

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        try:
            peer_did = is_peer_did(did)
        except Exception as e:
            raise DIDNotFound(f"peer_did is not formatted correctly: {did}") from e
        if peer_did:
            did_doc = resolve_peer_did(did)
        else:
            raise DIDNotFound(f"did is not a peer did: {did}") from e

        return did_doc.dict()



class PeerDID3Resolver(BaseDIDResolver):
    """Peer DID Resolver."""

    def __init__(self):
        """Initialize Key Resolver."""
        super().__init__(ResolverType.NATIVE)

    async def setup(self, context: InjectionContext):
        """Perform required setup for Key DID resolution."""

    @property
    def supported_did_regex(self) -> Pattern:
        """Return supported_did_regex of Key DID Resolver."""
        return re.compile(r"^did:peer:3(.*)")

    async def _resolve(
        self,
        profile: Profile,
        did: str,
        service_accept: Optional[Sequence[Text]] = None,
    ) -> dict:
        """Resolve a Key DID."""
        if did.startswith('did:peer:3'):
            # retrieve did_doc from storage using did:peer:3 
            did_doc, rec = await BaseConnectionManager(profile).fetch_did_document(did=did)
        else:
            raise DIDNotFound(f"did is not a peer did: {did}") from e

        return did_doc.dict()



def gen_did_peer_3(peer_did_2 : Union[str,DID]) -> Tuple[DID,DIDDocument]:
    if not peer_did_2.startswith("did:peer:2"):
        raise MalformedPeerDIDError("did:peer:2 expected")
    
    content = to_multibase(sha256(peer_did_2.lstrip("did:peer:2").encode()).digest(),MultibaseFormat.BASE58)
    dp3 = DID("did:peer:3"+content)

    doc = resolve_peer_did(peer_did_2)
    convert_to_did_peer_3_document(dp3,doc)
    return dp3, doc

def _replace_all_values(input,org,new):
    for k,v in input.items():
        typ = type(v)
        if isinstance(v,type(dict)):
            _replace_all_values(v,org,new)    
        if isinstance(v,List):
            for i,item in enumerate(v):
                if isinstance(item,type(dict)):
                    _replace_all_values(item,org,new)            
                elif isinstance(item,str) or isinstance(item,DID) or isinstance(item,DIDUrl):
                    v.pop(i)
                    v.append(item.replace(org,new,1))
                elif hasattr(item,"__dict__"):
                    _replace_all_values(item.__dict__,org,new) 
                else:
                    pass
                 
        elif isinstance(v,str) or isinstance(v,DID) or isinstance(v,DIDUrl):
            input[k] = v.replace(org,new,1)
        else:
            pass

def convert_to_did_peer_3_document(dp3, dp2_document:DIDDocument) -> None:
    dp2 = dp2_document.id
    _replace_all_values(dp2_document.__dict__, dp2,dp3)
    


