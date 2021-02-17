"""
DID Document Service Class.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from typing import List, Sequence, Union
from .verification_method import VerificationMethod
from .schemas.serviceschema import ServiceSchema
from ....resolver.did import DIDUrl


class Service:
    """
    Service specification to embed in DID document.

    Retains DIDs as raw values (orientated toward indy-facing operations),
    everything else as URIs (oriented toward W3C-facing operations).
    """

    def __init__(
        self,
        id: str,
        type: Union[str, List],
        service_endpoint: Union[str, Sequence, dict],
        recipient_keys: Union[Sequence, VerificationMethod] = None,
        routing_keys: Union[Sequence, VerificationMethod] = None,
        priority: int = 0,
    ):
        """
        Initialize the Service instance.

        Retain service specification particulars.

        Args:
            id: DID of DID document embedding service, specified raw
                (operation converts to URI)
            type: service type
            service_endpoint: service endpoint
            recipient_keys: recipient key or keys
            routing_keys: routing key or keys
            priority: service priority

        Raises:
            ValueError: on bad input controller DID

        """

        # Validation process
        DIDUrl.parse(id)

        self._id = id
        self._type = type or ""
        self._endpoint = service_endpoint or ""
        self._recip_keys = recipient_keys or []
        self._routing_keys = routing_keys or []
        self._priority = priority or 0

    @property
    def id(self) -> str:
        """Service identifier getter."""

        return self._id

    @id.setter
    def id(self, value: str):
        """Service identifier setter."""

        # Validation process
        DIDUrl.parse(value)
        self._id = value

    @property
    def type(self) -> Union[str, list]:
        """Service type getter."""

        return self._type

    @type.setter
    def type(self, value: Union[str, list]):
        """Service type setter."""

        self._type = value

    @property
    def recipient_keys(self) -> List[VerificationMethod]:
        """Service Recipient Key getter."""

        return self._recip_keys

    @recipient_keys.setter
    def recipient_keys(self, value: list):
        """Service Recipient Key setter."""

        self._recip_keys = value

    @property
    def routing_keys(self) -> List[VerificationMethod]:
        """Service Routing Keys getter."""

        return self._routing_keys

    @routing_keys.setter
    def routing_keys(self, value: list):
        """Service Routing Keys setter."""

        self._routing_keys = value

    @property
    def service_endpoint(self) -> str:
        """Service Endpoint getter."""

        return self._endpoint

    @service_endpoint.setter
    def service_endpoint(self, value: Union[str, dict, list]):
        """Service Endpoint setter."""

        self._endpoint = value

    @property
    def priority(self) -> int:
        """Service Priority getter."""

        return self._priority

    @priority.setter
    def priority(self, value: int):
        """Service Priority setter."""
        self._priority = value

    def serialize(self) -> dict:
        """Return dict representation of service to embed in DID document."""

        schema = ServiceSchema()
        result = schema.dump(self)
        return result

    @classmethod
    def deserialize(cls, value: dict):
        """Return a Service object to embed in DID document.

        Args:
            value: dict representation of service
        """
        schema = ServiceSchema()
        service = schema.load(value)
        return service
