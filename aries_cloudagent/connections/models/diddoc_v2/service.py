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
from .publickey import PublicKey
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
        type: Union[str, List] = None,
        recipientKeys: Union[Sequence, PublicKey] = None,
        routingKeys: Union[Sequence, PublicKey] = None,
        serviceEndpoint: Union[str, Sequence, dict] = None,
        priority: str = None,
    ):
        """
        Initialize the Service instance.

        Retain service specification particulars.

        Args:
            id: DID of DID document embedding service, specified raw
                (operation converts to URI)
            type: service type
            recipientKeys: recipient key or keys
            routingKeys: routing key or keys
            serviceEndpoint: service endpoint
            priority: service priority

        Raises:
            ValueError: on bad input controller DID

        """

        if not id:
            raise ValueError("Missing ID in the Service instantation")

        args = (id, type, serviceEndpoint)

        if any(param is None for param in args):
            raise ValueError("Missing args in the Service instantation")

        self._id = id
        self._type = type
        self._endpoint = serviceEndpoint
        self._recip_keys = recipientKeys
        self._routing_keys = routingKeys
        self._priority = priority

    @property
    def id(self) -> str:
        """Service identifier getter"""

        return self._id

    @id.setter
    def id(self, value: str):
        """Service identifier setter"""

        # Validation process
        DIDUrl.parse(value)
        self._id = value

    @property
    def type(self) -> Union[str, list]:
        """Service type getter"""

        return self._type

    @type.setter
    def type(self, value: Union[str, list]):
        """Service type setter"""

        self._type = value

    @property
    def recipientKeys(self) -> List[PublicKey]:
        """Service Recipient Key getter"""

        return self._recip_keys

    @recipientKeys.setter
    def recipientKeys(self, value: list):
        """Service Recipient Key setter"""

        self._recip_keys = value

    @property
    def routingKeys(self) -> List[PublicKey]:
        """Service Routing Keys getter"""

        return self._routing_keys

    @routingKeys.setter
    def routingKeys(self, value: list):
        """Service Routing Keys setter"""

        self._routing_keys = value

    @property
    def serviceEndpoint(self) -> str:
        """Service Endpoint getter"""

        return self._endpoint

    @serviceEndpoint.setter
    def serviceEndpoint(self, value: Union[str, dict, list]):
        """Service Endpoint setter"""

        self._endpoint = value

    @property
    def priority(self) -> int:
        """Service Priority getter"""

        return self._priority

    @priority.setter
    def priority(self, value: int):
        """Service Priority setter"""
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
