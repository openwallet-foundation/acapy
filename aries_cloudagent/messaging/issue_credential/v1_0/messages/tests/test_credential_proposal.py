from ..credential_proposal import CredentialProposal
from ..inner.credential_preview import AttributePreview, CredentialPreview
from ...message_types import CREDENTIAL_PROPOSAL

from unittest import mock, TestCase


class TestCredentialProposal(TestCase):
    """Credential proposal tests"""

    preview = CredentialPreview(
        attributes=(
            AttributePreview.list_plain({'test': '123', 'hello': 'world'}) +
            [
                AttributePreview(
                    name='rich',
                    value='Abcd123=',
                    encoding='base64',
                    mime_type='image/jpeg'
                )
            ]
        )
    )

    def test_init(self):
        """Test initializer"""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=self.preview,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )
        assert credential_proposal.credential_proposal == self.preview

    def test_type(self):
        """Test type"""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=self.preview,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )

        assert credential_proposal._type == CREDENTIAL_PROPOSAL

    @mock.patch(
        "aries_cloudagent.messaging.issue_credential.v1_0.messages."
        + "credential_proposal.CredentialProposalSchema.load"
    )
    def test_deserialize(self, mock_credential_proposal_schema_load):
        """
        Test deserialize
        """
        obj = {
            'comment': "Hello World",
            'credential_proposal': [
                {
                    'name': 'name',
                    'mime-type': 'text/plain',
                    'value': 'Alexander Delarge'
                },
                {
                    'name': 'pic',
                    'mime-type': 'image/jpeg',
                    'encoding': 'base64',
                    'value': 'Abcd0123...'
                }
            ]
        }

        credential_proposal = CredentialProposal.deserialize(obj)
        mock_credential_proposal_schema_load.assert_called_once_with(obj)

        assert credential_proposal is mock_credential_proposal_schema_load.return_value

    @mock.patch(
        "aries_cloudagent.messaging.issue_credential.v1_0.messages."
        + "credential_proposal.CredentialProposalSchema.dump"
    )
    def test_serialize(self, mock_credential_proposal_schema_dump):
        """
        Test serialization.
        """
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=self.preview,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )

        credential_proposal_dict = credential_proposal.serialize()
        mock_credential_proposal_schema_dump.assert_called_once_with(credential_proposal)

        assert credential_proposal_dict is mock_credential_proposal_schema_dump.return_value


class TestCredentialProposalSchema(TestCase):
    """Test credential cred proposal schema"""

    credential_proposal = CredentialProposal(
        comment="Hello World",
        credential_proposal=TestCredentialProposal.preview,
        schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
        cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
    )

    def test_make_model(self):
        """Test making model."""
        data = self.credential_proposal.serialize()
        model_instance = CredentialProposal.deserialize(data)
        assert isinstance(model_instance, CredentialProposal)
