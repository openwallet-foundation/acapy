from ..credential_proposal import CredentialProposal
from ..inner.credential_preview import AttributePreview, CredentialPreview
from ...message_types import CREDENTIAL_PREVIEW, CREDENTIAL_PROPOSAL

from unittest import TestCase


CRED_PREVIEW = CredentialPreview(
    attributes=(
        AttributePreview.list_plain({"test": "123", "hello": "world"}) +
        [
            AttributePreview(
                name="icon",
                value="cG90YXRv",
                encoding="base64",
                mime_type="image/png"
            )
        ]
    )
)


class TestCredentialProposal(TestCase):
    """Credential proposal tests."""

    def test_init(self):
        """Test initializer."""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )
        assert credential_proposal.credential_proposal == CRED_PREVIEW

    def test_type(self):
        """Test type."""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )

        assert credential_proposal._type == CREDENTIAL_PROPOSAL

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            "comment": "Hello World",
            "credential_proposal": {
                "@type": CREDENTIAL_PREVIEW,
                "attributes": [
                    {
                        "name": "name",
                        "mime-type": "text/plain",
                        "value": "Alexander Delarge"
                    },
                    {
                        "name": "pic",
                        "mime-type": "image/png",
                        "encoding": "base64",
                        "value": "Abcd0123..."
                    }
                ]
            },
            "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        }

        cred_proposal = CredentialProposal.deserialize(obj)
        assert type(cred_proposal) == CredentialProposal

    def test_serialize(self):
        """Test serialization."""

        cred_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("@id")

        assert cred_proposal_dict == {
            "@type": CREDENTIAL_PROPOSAL,
            "comment": "Hello World",
            "credential_proposal": {
                "@type": CREDENTIAL_PREVIEW,
                "attributes": [
                    {
                        "name": "test",
                        "mime-type": "text/plain",
                        "value": "123"
                    },
                    {
                        "name": "hello",
                        "mime-type": "text/plain",
                        "value": "world"
                    },
                    {
                        "name": "icon",
                        "mime-type": "image/png",
                        "encoding": "base64",
                        "value": "cG90YXRv"
                    }
                ]
            },
            "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
            "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
        }


class TestCredentialProposalSchema(TestCase):
    """Test credential cred proposal schema."""

    credential_proposal = CredentialProposal(
        comment="Hello World",
        credential_proposal=CRED_PREVIEW,
        schema_id="GMm4vMw8LLrLJjp81kRRLp:2:tails_load:1560364003.0",
        cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag"
    )

    def test_make_model(self):
        """Test making model."""
        data = self.credential_proposal.serialize()
        model_instance = CredentialProposal.deserialize(data)
        assert isinstance(model_instance, CredentialProposal)
