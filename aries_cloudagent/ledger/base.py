"""Ledger base class."""

from abc import ABC, abstractmethod, ABCMeta
import re
from typing import Tuple, Sequence


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
            self, schema_name: str, schema_version: str, attribute_names: Sequence[str]
    ) -> Tuple[str, dict]:
        """
        Send schema to ledger.

        Args:
            schema_name: The schema name
            schema_version: The schema version
            attribute_names: A list of schema attributes

        """

    @abstractmethod
    def get_revoc_reg_def(self, revoc_reg_id):
        """Look up a revocation registry definition by ID."""
        pass

    @abstractmethod
    def send_revoc_reg_def(self, revoc_reg_def, issuer_did):
        """Publish a revocation registry definition to the ledger."""
        pass

    @abstractmethod
    def send_revoc_reg_entry(self, revoc_reg_id, revoc_def_type, revoc_reg_entry, issuer_did):
        """Publish a revocation registry entry to the ledger."""
        pass

    @abstractmethod
    def create_and_send_credential_definition(self, schema_id, tag, support_revocation):
        """
        Send credential definition to ledger and store relevant key matter in wallet.

        Args:
            schema_id: The schema id of the schema to create cred def for
            tag: Optional tag to distinguish multiple credential definitions
            support_revocation: Optional flag to enable revocation for this cred def

        """
        pass

    @abstractmethod
    def get_credential_definition(self, credential_definition_id):
        """
        Get a credential definition from the cache if available, otherwise the ledger.

        Args:
            credential_definition_id: The schema id of the schema to fetch cred def for

        """
        pass

    @abstractmethod
    def get_revoc_reg_delta(self, revoc_reg_id, timestamp_from, timestamp_to):
        """Look up a revocation registry delta by ID."""
        pass

    @abstractmethod
    def get_schema(self, schema_id):
        """
        Get a schema from the cache if available, otherwise fetch from the ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        """
        pass