"""Ledger base class."""

from abc import ABC, abstractmethod, ABCMeta
import re
from typing import Tuple, Sequence

from ..issuer.base import BaseIssuer


class BaseLedger(ABC, metaclass=ABCMeta):
    """Base class for ledger."""

    LEDGER_TYPE = None

    async def __aenter__(self) -> "BaseLedger":
        """
        Context manager entry.

        Returns:
            The current instance

        """
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""

    @property
    @abstractmethod
    def type(self) -> str:
        """Accessor for the ledger type."""

    @abstractmethod
    async def get_key_for_did(self, did: str) -> str:
        """Fetch the verkey for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """

    @abstractmethod
    async def get_endpoint_for_did(self, did: str) -> str:
        """Fetch the endpoint for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """

    @abstractmethod
    async def update_endpoint_for_did(self, did: str, endpoint: str) -> bool:
        """Check and update the endpoint on the ledger.

        Args:
            did: The ledger DID
            endpoint: The endpoint address
        """

    @abstractmethod
    async def register_nym(
        self, did: str, verkey: str, alias: str = None, role: str = None
    ):
        """
        Register a nym on the ledger.

        Args:
            did: DID to register on the ledger.
            verkey: The verification key of the keypair.
            alias: Human-friendly alias to assign to the DID.
            role: For permissioned ledgers, what role should the new DID have.
        """

    @abstractmethod
    def nym_to_did(self, nym: str) -> str:
        """Format a nym with the ledger's DID prefix."""

    @abstractmethod
    async def rotate_public_did_keypair(self, next_seed: str = None) -> None:
        """
        Rotate keypair for public DID: create new key, submit to ledger, update wallet.

        Args:
            next_seed: seed for incoming ed25519 keypair (default random)
        """

    def did_to_nym(self, did: str) -> str:
        """Remove the ledger's DID prefix to produce a nym."""
        if did:
            return re.sub(r"^did:\w+:", "", did)

    async def get_txn_author_agreement(self, reload: bool = False):
        """Get the current transaction author agreement, fetching it if necessary."""

    async def fetch_txn_author_agreement(self):
        """Fetch the current AML and TAA from the ledger."""

    async def accept_txn_author_agreement(
        self, taa_record: dict, mechanism: str, accept_time: int = None
    ):
        """Save a new record recording the acceptance of the TAA."""

    async def get_latest_txn_author_acceptance(self):
        """Look up the latest TAA acceptance."""

    def taa_digest(self, version: str, text: str):
        """Generate the digest of a TAA record."""

    @abstractmethod
    async def create_and_send_schema(
        self,
        issuer: BaseIssuer,
        schema_name: str,
        schema_version: str,
        attribute_names: Sequence[str],
    ) -> Tuple[str, dict]:
        """
        Send schema to ledger.

        Args:
            issuer: The issuer instance to use for schema creation
            schema_name: The schema name
            schema_version: The schema version
            attribute_names: A list of schema attributes

        """

    @abstractmethod
    async def get_revoc_reg_def(self, revoc_reg_id: str) -> dict:
        """Look up a revocation registry definition by ID."""

    @abstractmethod
    async def send_revoc_reg_def(self, revoc_reg_def: dict, issuer_did: str = None):
        """Publish a revocation registry definition to the ledger."""

    @abstractmethod
    async def send_revoc_reg_entry(
        self,
        revoc_reg_id: str,
        revoc_def_type: str,
        revoc_reg_entry: dict,
        issuer_did: str = None,
    ):
        """Publish a revocation registry entry to the ledger."""

    @abstractmethod
    async def create_and_send_credential_definition(
        self,
        issuer: BaseIssuer,
        schema_id: str,
        signature_type: str = None,
        tag: str = None,
        support_revocation: bool = False,
    ) -> Tuple[str, dict]:
        """
        Send credential definition to ledger and store relevant key matter in wallet.

        Args:
            issuer: The issuer instance to use for credential definition creation
            schema_id: The schema id of the schema to create cred def for
            signature_type: The signature type to use on the credential definition
            tag: Optional tag to distinguish multiple credential definitions
            support_revocation: Optional flag to enable revocation for this cred def

        """

    @abstractmethod
    async def get_credential_definition(self, credential_definition_id: str) -> dict:
        """
        Get a credential definition from the cache if available, otherwise the ledger.

        Args:
            credential_definition_id: The schema id of the schema to fetch cred def for

        """

    @abstractmethod
    async def get_revoc_reg_delta(
        self, revoc_reg_id: str, timestamp_from=0, timestamp_to=None
    ) -> (dict, int):
        """Look up a revocation registry delta by ID."""

    @abstractmethod
    async def get_schema(self, schema_id: str) -> dict:
        """
        Get a schema from the cache if available, otherwise fetch from the ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        """

    @abstractmethod
    async def get_revoc_reg_entry(self, revoc_reg_id: str, timestamp: int):
        """Get revocation registry entry by revocation registry ID and timestamp."""
