from asynctest import TestCase as AsyncTestCase

from ..endpoint_type import EndpointType


class TestEndpointType(AsyncTestCase):
    async def test_endpoint_type(self):
        assert EndpointType.ENDPOINT is EndpointType.get("endpoint")
        assert EndpointType.PROFILE is EndpointType.get("PROFILE")
        assert EndpointType.LINKED_DOMAINS is EndpointType.get("linked_domains")
        assert EndpointType.get("no-such-type") is None
        assert EndpointType.get(None) is None

        assert EndpointType.PROFILE.w3c == "Profile"
        assert EndpointType.PROFILE.indy == "profile"
        assert EndpointType.ENDPOINT.w3c == "Endpoint"
        assert EndpointType.ENDPOINT.indy == "endpoint"
        assert EndpointType.LINKED_DOMAINS.w3c == "LinkedDomains"
        assert EndpointType.LINKED_DOMAINS.indy == "linked_domains"
