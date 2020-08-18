"""Ledger utilities."""

from enum import Enum

TAA_ACCEPTED_RECORD_TYPE = "taa_accepted"


class EndpointType(Enum):
    """Enum for endpoint/service types."""

    ENDPOINT = "endpoint"
    PROFILE = "Profile"
    LINKED_DOMAINS = "LinkedDomains"
