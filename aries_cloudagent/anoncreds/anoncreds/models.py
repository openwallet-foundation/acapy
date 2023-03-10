"""AnonCreds Objects"""
from typing import Any, Dict, List, Optional
from typing_extensions import Literal
from dataclasses import dataclass


@dataclass
class AnonCredsSchema:
    """AnonCredsSchema"""

    issuerId: str
    attrNames: List[str]
    name: str
    version: str


@dataclass
class AnonCredsRegistryGetSchema:
    """AnonCredsRegistryGetSchema"""

    schema: AnonCredsSchema
    schema_id: str
    resolution_metadata: Dict[str, Any]
    schema_metadata: Dict[str, Any]


# TODO: determine types for `primary` and `revocation`
@dataclass
class AnonCredsCredentialDefinitionValue:
    """AnonCredsCredentialDefinitionValue"""

    primary: Any
    revocation: Optional[Any]


@dataclass
class AnonCredsCredentialDefinition:
    """AnonCredsCredentialDefinition"""

    issuerId: str
    schemaId: str
    type: Literal["CL"]
    tag: str
    value: AnonCredsCredentialDefinitionValue


@dataclass
class AnonCredsRegistryGetCredentialDefinition:
    """AnonCredsRegistryGetCredentialDefinition"""

    credential_definition: AnonCredsCredentialDefinition
    credential_definition_id: str
    resolution_metadata: Dict[str, Any]
    credential_definition_metadata: Dict[str, Any]


@dataclass
class AnonCredsRevocationRegistryDefinition:
    """AnonCredsRevocationRegistryDefinition"""

    issuerId: str
    type: Literal["CL_ACCUM"]
    credDefId: str
    tag: str
    # TODO: determine type for `publicKeys`
    publicKeys: Any
    maxCredNum: int
    tailsLocation: str
    tailsHash: str


@dataclass
class AnonCredsRegistryGetRevocationRegistryDefinition:
    """AnonCredsRegistryGetRevocationRegistryDefinition"""

    revocation_registry: AnonCredsRevocationRegistryDefinition
    revocation_registry_id: str
    resolution_metadata: Dict[str, Any]
    revocation_registry_metadata: Dict[str, Any]


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
