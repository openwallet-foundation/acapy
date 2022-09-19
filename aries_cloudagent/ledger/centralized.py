"""Centralized ledger implementation."""

import json
import logging
from datetime import date, datetime
from typing import List, Sequence, Tuple

from aiohttp import (
    ClientSession,
)

from .base import BaseLedger, Role
from .endpoint_type import EndpointType
from .error import (
    BadLedgerRequestError,
    LedgerConfigError,
    LedgerError,
    LedgerTransactionError
)
from .util import TAA_ACCEPTED_RECORD_TYPE
from ..core.profile import Profile
from ..indy.issuer import DEFAULT_CRED_DEF_TAG, IndyIssuer, IndyIssuerError
from ..storage.base import StorageRecord
from ..storage.indy import IndySdkStorage
from ..utils import sentinel
from ..wallet.base import BaseWallet
from ..wallet.did_info import DIDInfo
from ..wallet.util import full_verkey

LOGGER = logging.getLogger(__name__)

GENESIS_TRANSACTION_FILE = "indy_genesis_transactions.txt"


class CentralizedSdkLedger(BaseLedger):
    """Centralized ledger class."""

    async def is_ledger_read_only(self) -> bool:
        """Accessor for the ledger read-only flag."""
        pass

    async def fetch_schema_by_seq_no(
            self,
            seq_no: int
    ) -> dict:
        """
        Fetch a schema by its sequence number.

        Args:
            seq_no: schema ledger sequence number

        Returns:
            Indy schema dict

        """
        pass

    async def _create_schema_request(
            self,
            public_info: DIDInfo,
            schema_json: str,
            write_ledger: bool = True,
            endorser_did: str = None
    ):
        """Create the ledger request for publishing a schema."""
        pass

    async def _create_credential_definition_request(
            self,
            public_info: DIDInfo,
            credential_definition_json: str,
            write_ledger: bool = True,
            endorser_did: str = None
    ):
        """Create the ledger request for publishing a credential definition."""
        pass

    BACKEND_NAME = "centralized"

    def __init__(
            self,
            pool: None,
            profile: Profile,
    ):
        """
        Initialize a CentralizedSdkLedger instance.

        Args:
            pool: The pool instance handling the raw ledger connection
            profile: The instantiated profile
        """
        self.pool = None
        self.profile = profile
        self.ledger_url = self.get_ledger_url(
            profile.settings.get_value("ledger.genesis_transactions")
        )

    @staticmethod
    def get_ledger_url(genesis_data) -> str:
        """
        Retrieve the URL to access the centralized ledger.

        Args:
            genesis_data: The genesis file content.

        Returns:
            The centralized ledger URL.
        """

        if not genesis_data:
            raise LedgerConfigError(
                "Cannot connect to the centralized ledger: missing genesis file")
        genesis_data = json.loads(genesis_data)
        if "client_ip" not in genesis_data:
            raise LedgerConfigError(
                "Bad genesis file for CentralizedSdkLedger: "
                "missing required field \"client_ip\"")
        elif "client_port" not in genesis_data:
            raise LedgerConfigError(
                "Bad genesis file for CentralizedSdkLedger: "
                "missing required field \"client_data\"")
        else:
            return genesis_data["client_ip"] + ":" + genesis_data["client_port"]

    @property
    def read_only(self) -> bool:
        """Accessor for the ledger read-only flag."""
        return False

    async def __aenter__(self) -> "CentralizedSdkLedger":
        """
        Context manager entry.

        Returns:
            The current instance

        """
        await super().__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Context manager exit."""
        await super().__aexit__(exc_type, exc, tb)

    async def get_wallet_public_did(self) -> DIDInfo:
        """Fetch the public DID from the wallet."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            return await wallet.get_public_did()

    async def txn_endorse(
            self,
            request_json: str,
            endorse_did: DIDInfo = None,
    ) -> str:
        """Endorse a (signed) ledger transaction."""
        return ""

    async def txn_submit(
            self,
            request_json: str,
            sign: bool = None,
            taa_accept: bool = None,
            sign_did: DIDInfo = sentinel,
            write_ledger: bool = True,
    ) -> str:
        """Submit a signed (and endorsed) transaction to the ledger."""
        return ""

    async def create_and_send_schema(
            self,
            issuer: IndyIssuer,
            schema_name: str,
            schema_version: str,
            attribute_names: Sequence[str],
            write_ledger: bool = True,
            endorser_did: str = None,
    ) -> Tuple[str, dict]:
        """
        Send schema to ledger.

        Args:
            issuer: The issuer instance creating the schema
            schema_name: The schema name
            schema_version: The schema version
            attribute_names: A list of schema attributes
            write_ledger: True if we want to write on the ledger
            endorser_did: The endorser DID
        """

        public_info = await self.get_wallet_public_did()
        if not public_info:
            raise BadLedgerRequestError("Cannot publish schema without a public DID")

        schema_info = await self.check_existing_schema(
            public_info.did, schema_name, schema_version, attribute_names
        )
        if schema_info:
            LOGGER.warning("Schema already exists on ledger. Returning details.")
            schema_id, schema_def = schema_info
        else:
            try:
                schema_id, schema_json = await issuer.create_schema(
                    public_info.did,
                    schema_name,
                    schema_version,
                    attribute_names,
                )
            except IndyIssuerError as err:
                raise LedgerError(err.message) from err
            schema_def = json.loads(schema_json)

            async with ClientSession() as session:
                async with session.post(self.ledger_url + "/api/schema/" + schema_id,
                                        json=schema_def) as resp:
                    if resp.status != 200:
                        raise LedgerTransactionError(
                            f"Error occurred creating the schema {schema_id}")
        return schema_id, schema_def

    async def check_existing_schema(
            self,
            public_did: str,
            schema_name: str,
            schema_version: str,
            attribute_names: Sequence[str],
    ) -> Tuple[str, dict]:
        """
        Check if a schema has already been published.

        Args:
            public_did: The public did used for publishing the schema
            schema_name: The schema name
            schema_version: The schema version
            attribute_names: Schema attributes to compare
        """

        fetch_schema_id = f"{public_did}:2:{schema_name}:{schema_version}"
        schema = await self.fetch_schema_by_id(fetch_schema_id)
        if schema:
            fetched_attrs = schema["attrNames"].copy()
            fetched_attrs.sort()
            cmp_attrs = list(attribute_names)
            cmp_attrs.sort()
            if fetched_attrs != cmp_attrs:
                raise LedgerTransactionError(
                    "Schema already exists on ledger, but attributes do not match: "
                    + f"{schema_name}:{schema_version} {fetched_attrs} != {cmp_attrs}"
                )
            return fetch_schema_id, schema

    async def get_schema(self, schema_id: str) -> dict:
        """
        Get a schema from the cache if available, otherwise fetch from the ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        """
        return await self.fetch_schema_by_id(schema_id)

    async def fetch_schema_by_id(self, schema_id: str) -> dict:
        """
        Get schema from ledger.

        Args:
            schema_id: The schema id (or stringified sequence number) to retrieve

        Returns:
            Indy schema dict

        """
        async with ClientSession() as session:
            async with session.get(self.ledger_url + "/api/schema/" + schema_id) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

    async def create_and_send_credential_definition(
            self,
            issuer: IndyIssuer,
            schema_id: str,
            signature_type: str = None,
            tag: str = None,
            support_revocation: bool = False,
            write_ledger: bool = True,
            endorser_did: str = None,
    ) -> Tuple[str, dict, bool]:
        """
        Send credential definition to ledger and store relevant key matter in wallet.

        Args:
            issuer: The issuer instance to use for credential definition creation
            schema_id: The schema id of the schema to create cred def for
            signature_type: The signature type to use on the credential definition
            tag: Optional tag to distinguish multiple credential definitions
            support_revocation: Optional flag to enable revocation for this cred def

        Returns:
            Tuple with cred def id, cred def structure, and whether it's novel

        """
        public_info = await self.get_wallet_public_did()
        if not public_info:
            raise BadLedgerRequestError(
                "Cannot publish credential definition without a public DID"
            )

        schema = await self.get_schema(schema_id)
        if not schema:
            raise LedgerError(f"Ledger centralized has no schema {schema_id}")

        novel = False

        # check if cred def is on ledger already
        for test_tag in [tag] if tag else ["tag", DEFAULT_CRED_DEF_TAG]:
            credential_definition_id = issuer.make_credential_definition_id(
                public_info.did, schema, signature_type, test_tag
            )
            ledger_cred_def = await self.fetch_credential_definition(
                credential_definition_id
            )
            if ledger_cred_def:
                LOGGER.warning(
                    "Credential definition %s already exists on centralized ledger",
                    credential_definition_id
                )

                try:
                    async with self.profile.session() as session:
                        wallet = session.inject(BaseWallet)
                        if not await issuer.credential_definition_in_wallet(
                                credential_definition_id
                        ):
                            raise LedgerError(
                                f"Credential definition {credential_definition_id} is on "
                                f"centralized ledger but not in wallet "
                                f"{wallet.opened.name}"
                            )
                except IndyIssuerError as err:
                    raise LedgerError(err.message) from err
                break
            else:  # no such cred def on ledger
                try:
                    async with self.profile.session() as session:
                        wallet = session.inject(BaseWallet)
                        if await issuer.credential_definition_in_wallet(
                                credential_definition_id
                        ):
                            raise LedgerError(
                                f"Credential definition {credential_definition_id} "
                                f"is in wallet {wallet.opened.name} "
                                f"but not on centralized ledger"
                            )
                except IndyIssuerError as err:
                    raise LedgerError(err.message) from err

            # Cred def is neither on ledger nor in wallet: create and send it
            novel = True
            try:
                (
                    credential_definition_id,
                    credential_definition_json,
                ) = await issuer.create_and_store_credential_definition(
                    public_info.did,
                    schema,
                    signature_type,
                    tag,
                    support_revocation,
                )
            except IndyIssuerError as err:
                raise LedgerError(err.message) from err

            async with ClientSession() as session:
                request_json = json.loads(credential_definition_json)
                async with session.post(
                        self.ledger_url
                        + "/api/credentialDefinition/"
                        + credential_definition_id,
                        json=request_json
                ) as resp:
                    if resp.status != 200:
                        raise LedgerTransactionError(
                            f"Error occurred creating the credential definition "
                            f"{credential_definition_id}"
                        )
                    else:
                        resp = await resp.json()
                        if not write_ledger:
                            return credential_definition_id, {"signed_txn": resp}, novel
                        return credential_definition_id, request_json, novel

    async def get_credential_definition(self, credential_definition_id: str) -> dict:
        """
        Get a credential definition from the cache if available, otherwise the ledger.

        Args:
            credential_definition_id: The schema id of the schema to fetch cred def for

        """
        return await self.fetch_credential_definition(credential_definition_id)

    async def fetch_credential_definition(self, credential_definition_id: str) -> dict:
        """
        Get a credential definition from the ledger by id.

        Args:
            credential_definition_id: The cred def id of the cred def to fetch

        """
        async with ClientSession() as session:
            async with session.get(
                    self.ledger_url
                    + "/api/credentialDefinition/"
                    + credential_definition_id
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

    async def get_key_for_did(self, did: str) -> str:
        """Fetch the verkey for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """
        did_doc = await self.get_did_doc_for_did(did)
        return full_verkey(did, did_doc["verKey"]) if did_doc else None

    async def get_did_doc_for_did(self, did: str) -> dict:
        """
        Fetch from the ledger the DIDDoc associated with the given DID.
        """
        nym = self.did_to_nym(did)
        async with ClientSession() as session:
            async with session.get(self.ledger_url + "/api/did/" + nym) as resp:
                nym_info = await resp.json()
                return nym_info

    async def get_all_endpoints_for_did(self, did: str) -> dict:
        """Fetch all endpoints for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
        """
        did_doc = await self.get_did_doc_for_did(did)

        if did_doc and 'endpoint' in did_doc:
            endpoints = did_doc['endpoint']
        else:
            endpoints = None

        return endpoints

    async def get_endpoint_for_did(
            self, did: str, endpoint_type: EndpointType = None
    ) -> str:
        """Fetch the endpoint for a ledger DID.

        Args:
            did: The DID to look up on the ledger or in the cache
            endpoint_type: The type of the endpoint. If none given, returns all
        """
        response_json = await self.get_did_doc_for_did(did)
        if response_json and "endpoint" in response_json:
            endpoint = response_json["endpoint"]
            if endpoint_type in endpoint:
                return endpoint[endpoint_type]
        return None

    async def update_endpoint_for_did(
            self,
            did: str,
            endpoint: str,
            endpoint_type: EndpointType = None,
            write_ledger: bool = True,
            endorser_did: str = None,
            routing_keys: List[str] = None,
    ) -> bool:
        """Check and update the endpoint on the ledger.

        Args:
            did: The ledger DID
            endpoint: The endpoint address
            endpoint_type: The type of the endpoint
            write_ledger: True if we want to write on the ledger
            endorser_did: The endorser DID
            routing_keys: The routing keys
        """
        public_info = await self.get_wallet_public_did()
        if not public_info:
            raise BadLedgerRequestError(
                "Cannot update endpoint at ledger without a public DID"
            )

        if not endpoint_type:
            endpoint_type = EndpointType.ENDPOINT

        all_exist_endpoints = await self.get_all_endpoints_for_did(did)
        exist_endpoint_of_type = (
            all_exist_endpoints.get(endpoint_type.indy, None)
            if all_exist_endpoints
            else None
        )

        if exist_endpoint_of_type != endpoint:
            request_json = await self.get_did_doc_for_did(did)
            if all_exist_endpoints:
                all_exist_endpoints[endpoint_type.indy] = endpoint
                request_json["endpoint"] = all_exist_endpoints
            else:
                request_json["endpoint"] = {endpoint_type.indy: endpoint}
            async with ClientSession() as session:
                async with session.post(self.ledger_url + "/api/did/" + did,
                                        json=request_json) as resp:
                    if resp.status != 200:
                        raise LedgerTransactionError(
                            f"Error occurred updating the endpoint for the did {did}")
                    return True
        return False

    async def register_nym(
            self,
            did: str,
            verkey: str,
            alias: str = None,
            role: str = None,
            write_ledger: bool = True,
            endorser_did: str = None,
    ) -> Tuple[bool, dict]:
        """
        Register a nym on the ledger.

        Args:
            did: DID to register on the ledger.
            verkey: The verification key of the keypair.
            alias: Human-friendly alias to assign to the DID.
            role: For permissioned ledgers, what role should the new DID have.
        """
        request_json = {
            "did": did,
            "verKey": verkey,
            "alias": alias,
            "role": role,
            "endpoint": await self.get_all_endpoints_for_did(did)
        }
        async with ClientSession() as session:
            async with session.post(self.ledger_url + "/api/did/" + did,
                                    json=request_json) as resp:
                if resp.status != 200:
                    raise LedgerTransactionError(f"Error occurred creating the did {did}")
                resp = await resp.json()
                return True, {"signed_txn": resp}

    async def credential_definition_id2schema_id(self, credential_definition_id):
        """
        From a credential definition, get the identifier for its schema.

        Args:
            credential_definition_id: The identifier of the credential definition
                from which to identify a schema
        """

        # scrape schema id or sequence number from cred def id
        tokens = credential_definition_id.split(":")
        if len(tokens) == 8:  # node protocol >= 1.4: cred def id has 5 or 8 tokens
            return ":".join(tokens[3:7])  # schema id spans 0-based positions 3-6

        # get txn by sequence number, retrieve schema identifier components
        seq_no = tokens[3]
        return (await self.get_schema(seq_no))["id"]

    async def get_nym_role(self, did: str) -> Role:
        """
        Return the role of the input public DID's NYM on the ledger.

        Args:
            did: DID to query for role on the ledger.
        """
        response_json = await self.get_did_doc_for_did(did)
        if response_json and "role" in response_json:
            role = response_json["role"]
        else:
            role = None

        return Role.get(role)

    def nym_to_did(self, nym: str) -> str:
        """Format a nym with the ledger's DID prefix."""
        if nym:
            # remove any existing prefix
            nym = self.did_to_nym(nym)
            return f"did:sov:{nym}"

    async def rotate_public_did_keypair(self, next_seed: str = None) -> None:
        """
        Rotate keypair for public DID: create new key, submit to ledger, update wallet.

        Args:
            next_seed: seed for incoming ed25519 keypair (default random)
        """
        # generate new key
        public_info = await self.get_wallet_public_did()
        public_did = public_info.did
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            verkey = await wallet.rotate_did_keypair_start(public_did, next_seed)

            # get current nym from ledger
            current_nym = await self.get_did_doc_for_did(public_did)
            # submit to ledger (retain role and alias)
            alias = current_nym["alias"]
            role_token = current_nym["role"]
            await self.register_nym(public_did, verkey, alias, role_token)

            # update wallet
            await wallet.rotate_did_keypair_apply(public_did)

    async def get_txn_author_agreement(self, reload: bool = False) -> dict:
        """Get the current transaction author agreement, fetching it if necessary."""
        return await self.fetch_txn_author_agreement()

    async def fetch_txn_author_agreement(self) -> dict:
        """Fetch the current AML and TAA from the ledger."""
        return {
            "aml_record": None,
            "taa_record": None,
            "taa_required": None,
        }

    async def get_indy_storage(self) -> IndySdkStorage:
        """Get an IndySdkStorage instance for the current wallet."""
        async with self.profile.session() as session:
            wallet = session.inject(BaseWallet)
            return IndySdkStorage(wallet.opened)

    def taa_rough_timestamp(self) -> int:
        """Get a timestamp accurate to the day.

        Anything more accurate is a privacy concern.
        """
        return int(datetime.combine(date.today(), datetime.min.time()).timestamp())

    async def accept_txn_author_agreement(
            self, taa_record: dict, mechanism: str, accept_time: int = None
    ):
        """Save a new record recording the acceptance of the TAA."""
        if not accept_time:
            accept_time = self.taa_rough_timestamp()
        acceptance = {
            "text": taa_record["text"],
            "version": taa_record["version"],
            "digest": taa_record["digest"],
            "mechanism": mechanism,
            "time": accept_time,
        }
        record = StorageRecord(
            TAA_ACCEPTED_RECORD_TYPE,
            json.dumps(acceptance)
        )
        storage = await self.get_indy_storage()
        await storage.add_record(record)

    async def get_latest_txn_author_acceptance(self) -> dict:
        """Look up the latest TAA acceptance."""
        storage = await self.get_indy_storage()
        found = await storage.find_all_records(TAA_ACCEPTED_RECORD_TYPE)
        if found:
            records = list(json.loads(record.value) for record in found)
            records.sort(key=lambda v: v["time"], reverse=True)
            acceptance = records[0]
        else:
            acceptance = {}
        return acceptance

    async def get_revoc_reg_def(self, revoc_reg_id: str) -> dict:
        """Get revocation registry definition by ID; augment with ledger timestamp."""
        async with ClientSession() as session:
            async with session.get(
                    self.ledger_url
                    + "/api/revocationDefinition/"
                    + revoc_reg_id
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    return resp

    async def get_revoc_reg_entry(self, revoc_reg_id: str, timestamp: int):
        """Get revocation registry entry by revocation registry ID and timestamp."""
        async with ClientSession() as session:
            async with session.get(
                    url=self.ledger_url + "/api/revocationEntry/" + revoc_reg_id,
                    params={"timestamp": timestamp} if timestamp else {}
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
        rev_reg_delta = resp.get("value")
        return rev_reg_delta, 0

    async def get_revoc_reg_delta(
            self, revoc_reg_id: str, fro=0, to=None
    ) -> Tuple[dict, int]:
        """
        Look up a revocation registry delta by ID.

        :param revoc_reg_id revocation registry id
        :param fro earliest EPOCH time of interest
        :param to latest EPOCH time of interest

        :returns delta response, delta timestamp
        """
        async with ClientSession() as session:
            async with session.get(
                    url=self.ledger_url + "/api/revocationDelta/" + revoc_reg_id,
                    params={"timestamp": to} if to else {}
            ) as resp:
                if resp.status == 200:
                    resp = await resp.json()
        rev_reg_delta = resp.get("value")
        timestamp = resp.get("timestamp")
        return rev_reg_delta, timestamp

    async def send_revoc_reg_def(
            self,
            revoc_reg_def: dict,
            issuer_did: str = None,
            write_ledger: bool = True,
            endorser_did: str = None,
    ):
        """Publish a revocation registry definition to the ledger."""
        # NOTE - issuer DID could be extracted from the revoc_reg_def ID
        revoc_reg_def_id = revoc_reg_def["id"]
        async with ClientSession() as session:
            async with session.post(
                    self.ledger_url + "/api/revocationDefinition/" + revoc_reg_def_id,
                    json=revoc_reg_def
            ) as resp:
                if resp.status != 200:
                    raise LedgerTransactionError(
                        f"Error occurred creating "
                        f"the revocation definition {revoc_reg_def_id}"
                    )
                return {"result": resp}

    async def send_revoc_reg_entry(
            self,
            revoc_reg_id: str,
            revoc_def_type: str,
            revoc_reg_entry: dict,
            issuer_did: str = None,
            write_ledger: bool = True,
            endorser_did: str = None,
    ):
        """Publish a revocation registry entry to the ledger."""
        request_data = {
            "revocRegDefId": revoc_reg_id,
            "revocDefType": revoc_def_type,
            "value": revoc_reg_entry
        }
        async with ClientSession() as session:
            async with session.post(
                    self.ledger_url + "/api/revocationEntry/" + revoc_reg_id,
                    json=request_data
            ) as resp:
                if resp.status != 200:
                    raise LedgerTransactionError(
                        f"Error occurred creating the revocation entry {revoc_reg_id}")
                return {"result": resp}
