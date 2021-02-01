"""W3C DIDDoc Data Model.

Model defined here using W3C Decentrialized Identifiers v1.0 Working Draft 18
January 2021:

    https://w3c.github.io/did-core/

"""

import json
from typing import Sequence, Union
from operator import itemgetter
from .did import DID, DIDUrl


class ExternalResourceError(Exception):
    """Raised when dereference is not contained within the current document."""


def _index_ids_of_doc(doc: dict):
    index = {}

    def _visit(value):
        if isinstance(value, dict):
            if "id" in value:
                index[value["id"]] = value
            for nested in value.values():
                _visit(nested)
        elif isinstance(value, list):
            for nested in value:
                _visit(nested)

    _visit(doc)
    return index


class ResolvedDIDDoc:
    """DID Document returned by a Resolver."""

    OLD_AGENT_SERVICE_TYPE = "IndyAgent"
    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self, doc: dict):
        """Initialize Resolved DID Doc.

        Args:
            doc (dict): DID Document as resolved in dictionary representation.

        """
        self._doc = doc
        self._did = DID(doc["id"])
        self._index = _index_ids_of_doc(doc)

    @classmethod
    def from_json(cls, doc_json: str) -> "ResolvedDIDDoc":
        """Create ResolvedDIDDoc from json string."""
        return cls(json.loads(doc_json))

    @property
    def did(self):
        """Return the DID subject of this Document."""
        return self._did

    def didcomm_services(self) -> Sequence[dict]:
        """Return agent services in priority order."""

        def _valid_filter(service):
            return (
                "priority" in service
                and "recipientKeys" in service
                and "serviceEndpoint" in service
                and "type" in service
                and service["type"]
                in (self.OLD_AGENT_SERVICE_TYPE, self.AGENT_SERVICE_TYPE)
            )

        # Filter out all but didcomm services with expected properties
        services = filter(_valid_filter, self._doc.get("service", []))

        didcomm = filter(
            lambda service: service["type"] == self.AGENT_SERVICE_TYPE, services
        )
        old = filter(
            lambda service: service["type"] == self.OLD_AGENT_SERVICE_TYPE, services
        )

        # Prioritize agent service type over old agent service type
        # then sort by priority
        return [
            *(sorted(didcomm, key=itemgetter("priority"))),
            *(sorted(old, key=itemgetter("priority"))),
        ]

    def dereference(self, did_url: Union[str, DIDUrl]):
        """Dereference values contained in this DID Document."""
        if isinstance(did_url, str):
            parsed = DIDUrl.parse(did_url)

        if self.did != parsed.did:
            raise ExternalResourceError(
                "{} is not contained in this DID Document".format(did_url)
            )

        if parsed.path or parsed.query:
            raise NotImplementedError(
                "Dereferencing DID URLs with paths or query parameters is not \
                supported yet."
            )

        return self._index.get(parsed.fragment)
