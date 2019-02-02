from ..agent_endpoint import AgentEndpoint, AgentEndpointSchema

from unittest import mock, TestCase


class TestAgentEndpoint(TestCase):
    did = "did"
    verkey = "verkey"
    uri = "uri"

    def test_init(self):
        agent_endpoint = AgentEndpoint(
            did=self.did,
            verkey=self.verkey,
            uri=self.uri
        )
        assert agent_endpoint.did == self.did
        assert agent_endpoint.verkey == self.verkey
        assert agent_endpoint.uri == self.uri
