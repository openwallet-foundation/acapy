from unittest import TestCase

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import CREDENTIAL_PREVIEW, CREDENTIAL_PROPOSAL

from ..credential_proposal import CredentialProposal
from ..inner.credential_preview import CredAttrSpec, CredentialPreview


CRED_PREVIEW = CredentialPreview(
    attributes=(
        CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
    )
)


class TestCredentialProposal(TestCase):
    """Credential proposal tests."""

    def test_init(self):
        """Test initializer."""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        )
        assert credential_proposal.credential_proposal == CRED_PREVIEW

    def test_type(self):
        """Test type."""
        credential_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        )

        assert credential_proposal._type == DIDCommPrefix.qualify_current(
            CREDENTIAL_PROPOSAL
        )

    def test_deserialize(self):
        """Test deserialize."""
        obj = {
            "comment": "Hello World",
            "credential_proposal": {
                "@type": DIDCommPrefix.qualify_current(CREDENTIAL_PREVIEW),
                "attributes": [
                    {"name": "name", "value": "Alexander Delarge"},
                    {"name": "pic", "mime-type": "image/png", "value": "Abcd0123..."},
                ],
            },
            "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        }

        cred_proposal = CredentialProposal.deserialize(obj)
        assert type(cred_proposal) == CredentialProposal

    def test_serialize(self):
        """Test serialization."""

        cred_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("@id")

        assert cred_proposal_dict == {
            "@type": DIDCommPrefix.qualify_current(CREDENTIAL_PROPOSAL),
            "comment": "Hello World",
            "credential_proposal": {
                "@type": DIDCommPrefix.qualify_current(CREDENTIAL_PREVIEW),
                "attributes": [
                    {"name": "test", "value": "123"},
                    {"name": "hello", "value": "world"},
                    {"name": "icon", "mime-type": "image/png", "value": "cG90YXRv"},
                ],
            },
            "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        }

    def test_serialize_no_proposal(self):
        """Test serialization."""

        cred_proposal = CredentialProposal(
            comment="Hello World",
            credential_proposal=None,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("@id")

        assert cred_proposal_dict == {
            "@type": DIDCommPrefix.qualify_current(CREDENTIAL_PROPOSAL),
            "comment": "Hello World",
            "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
            "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        }


class TestCredentialProposalSchema(TestCase):
    """Test credential cred proposal schema."""

    credential_proposals = [
        CredentialProposal(
            credential_proposal=CRED_PREVIEW,
        ),
        CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            cred_def_id="GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
        ),
        CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_id="GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1.0",
        ),
        CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_issuer_did="GMm4vMw8LLrLJjp81kRRLp",
        ),
        CredentialProposal(
            comment="Hello World",
            credential_proposal=CRED_PREVIEW,
            schema_name="ahoy",
            schema_version="1.0",
            issuer_did="GMm4vMw8LLrLJjp81kRRLp",
        ),
    ]

    def test_make_model(self):
        """Test making model."""
        for credential_proposal in self.credential_proposals:
            data = credential_proposal.serialize()
            model_instance = CredentialProposal.deserialize(data)
            assert isinstance(model_instance, CredentialProposal)
