"""Ledger utilities."""

from collections import namedtuple
from enum import Enum

EndpointTypeName = namedtuple("EndpointTypeName", "w3c indy")


class EndpointType(Enum):
    """Enum for endpoint/service types."""

    ENDPOINT = EndpointTypeName("Endpoint", "endpoint")
    PROFILE = EndpointTypeName("Profile", "profile")
    LINKED_DOMAINS = EndpointTypeName("LinkedDomains", "linked_domains")

    @staticmethod
    def get(name: str) -> "EndpointType":
        """Return enum instance corresponding to input string."""
        if name is None:
            return None

        for endpoint_type in EndpointType:
            if name.replace("_", "").lower() == endpoint_type.w3c.lower():
                return endpoint_type

        return None

    @property
    def w3c(self):
        """W3C name of endpoint type: externally-facing."""
        return self.value.w3c

    @property
    def indy(self):
        """Indy name of endpoint type: internally-facing, on ledger and in wallet."""
        return self.value.indy
