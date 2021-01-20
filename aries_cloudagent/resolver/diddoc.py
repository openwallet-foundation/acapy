"""W3C DIDDoc Data Model.

Model defined here using W3C Decentrialized Identifiers v1.0 Working Draft 18
January 2021:

    https://w3c.github.io/did-core/

"""

import json
from typing import Any, Dict, Sequence, Union
from operator import attrgetter


class ResolvedService:
    """Service element embedded in resolved DID Documents."""


class ResolvedDIDDoc:
    """DID Document returned by a Resolver."""

    OLD_AGENT_SERVICE_TYPE = "IndyAgent"
    AGENT_SERVICE_TYPE = "did-communication"

    def __init__(self, doc: Dict[str, Any]):
        """Initialize Resolved DID Doc.

        Args:
            doc (Dict[str, Any]): DID Document as resolved in dictionary representation.

        """
        self._doc = doc
        # Required properties
        self._id = doc["id"]

        # Optional properties
        if "service" in doc:
            self._service = {service["id"]: service for service in doc["service"]}

        if "verificationMethod" in doc:
            self._verification_method = dict(
                [(method["id"], method) for method in doc["verificationMethod"]]
            )

    @classmethod
    def from_json(cls, doc_json: str) -> "ResolvedDIDDoc":
        """Create ResolvedDIDDoc from json string."""
        return cls(json.loads(doc_json))

    def get(self, key: str, default: Any = None) -> Union[str, Dict, Sequence]:
        """Get a value from the DIDDoc.

        Args:
            key (str): key to retrieve
            default (Any): default value returned if key is absent

        """
        return self._doc.get(key, default)

    def service(self, id_: str):
        """Retrieve a service from the doc by ID."""
        return self._service[id_]

    def verification_method(self, id_: str):
        """Retrieve a verification method from the doc by ID."""
        return self._verification_method[id_]

    def didcomm_services(self) -> Sequence[Dict]:
        """Return agent services in priority order."""

        def _valid_filter(service):
            return (
                "priority" in service
                and "recipientKeys" in service
                and "serviceEndpoint" in service
                and "type" in service
                and (
                    service["type"] == self.OLD_AGENT_SERVICE_TYPE
                    or service["type"] == self.AGENT_SERVICE_TYPE
                )
            )

        # Filter out all but agent services with expected properties
        services = filter(_valid_filter, self._service.values())

        didcomm = filter(
            lambda service: service["type"] == self.AGENT_SERVICE_TYPE, services
        )
        old = filter(
            lambda service: service["type"] == self.OLD_AGENT_SERVICE_TYPE, services
        )

        # Prioritize agent service type over old agent service type
        # then sort by priority
        return [
            *(sorted(didcomm, key=attrgetter("priority"))),
            *(sorted(old, key=attrgetter("priority"))),
        ]
