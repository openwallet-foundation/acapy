"""AnonCreds Objects"""
from typing import Any, Dict, List, Optional
from typing_extensions import Literal
from dataclasses import dataclass



@dataclass
class AnonCredsRevocationList:
    """AnonCredsRevocationList"""

    issuerId: str
    revRegId: str
    revocationList: List[int]
    currentAccumulator: str
    timestamp: int


@dataclass
class AnonCredsRegistryGetRevocationList:
    """AnonCredsRegistryGetRevocationList"""

    revocation_list: AnonCredsRevocationList
    resolution_metadata: Dict[str, Any]
    revocation_registry_metadata: Dict[str, Any]
