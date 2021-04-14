from asynctest import TestCase as AsyncTestCase

from ......messaging.decorators.attach_decorator import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, CRED_20_PREVIEW, CRED_20_PROPOSAL

from ..cred_format import V20CredFormat
from ..cred_proposal import V20CredProposal, V20CredFormat
from ..inner.cred_preview import V20CredAttrSpec, V20CredPreview


TEST_PREVIEW = V20CredPreview(
    attributes=(
        V20CredAttrSpec.list_plain({"test": "123", "hello": "world"})
        + [V20CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
    )
)

TEST_INDY_FILTER = {
    "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
    "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
}


class TestV20CredProposal(AsyncTestCase):
    """Credential proposal tests."""

    async def test_init(self):
        """Test initializer."""
        cred_proposal = V20CredProposal(
            comment="Hello World",
            credential_preview=TEST_PREVIEW,
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(TEST_INDY_FILTER, ident="indy")
            ],
        )
        assert cred_proposal.credential_preview == TEST_PREVIEW
        assert cred_proposal.attachment() == TEST_INDY_FILTER
        assert cred_proposal._type == DIDCommPrefix.qualify_current(CRED_20_PROPOSAL)

    async def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_cred_proposal = V20CredProposal(
            comment="Test",
            formats=[V20CredFormat(attach_id="not_indy", format_="not_indy")],
            filters_attach=[
                AttachDecorator.data_base64(
                    ident="not_indy",
                    mapping=TEST_PREVIEW.serialize(),
                )
            ],
        )
        assert x_cred_proposal.attachment() is None

    async def test_deserialize(self):
        """Test deserialization."""
        obj = {
            "@type": "https://didcomm.org/issue-credential/2.0/propose-credential",
            "@id": "56dfd607-e03b-4175-8e36-c49329da891b",
            "comment": "Hello World",
            "credential_preview": {
                "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
                "attributes": [
                    {"name": "test", "value": "123"},
                    {"name": "hello", "value": "world"},
                    {"name": "icon", "mime-type": "image/png", "value": "cG90YXRv"},
                ],
            },
            "formats": [
                {
                    "attach_id": "indy",
                    "format": ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                }
            ],
            "filters~attach": [
                {
                    "@id": "indy",
                    "mime-type": "application/json",
                    "data": {
                        "base64": (
                            "eyJzY2hlbWFfaWQiOiAiR01tNHZNdzhMTHJMSmpw"
                            "ODFrUlJMcDoyOmFob3k6MTU2MDM2NDAwMy4wIiwg"
                            "ImNyZWRfZGVmX2lkIjogIkdNbTR2TXc4TExyTEpq"
                            "cDgxa1JSTHA6MzpDTDoxMjp0YWcifQ=="
                        )
                    },
                }
            ],
        }
        cred_proposal = V20CredProposal.deserialize(obj)
        assert type(cred_proposal) == V20CredProposal

        obj["filters~attach"][0]["data"]["base64"] = "eyJub3QiOiAiaW5keSJ9"  # not indy
        with self.assertRaises(BaseModelError):
            V20CredProposal.deserialize(obj)

        obj["filters~attach"][0]["@id"] = "xxx"
        with self.assertRaises(BaseModelError):
            V20CredProposal.deserialize(obj)

        obj["filters~attach"].append(  # more attachments than formats
            {
                "@id": "def",
                "mime-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
            }
        )
        with self.assertRaises(BaseModelError):
            V20CredProposal.deserialize(obj)

        cred_proposal.formats.append(  # unknown format: no validation
            V20CredFormat(
                attach_id="not_indy",
                format_="not_indy",
            )
        )
        obj = cred_proposal.serialize()
        obj["filters~attach"].append(
            {
                "@id": "not_indy",
                "mime-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
            }
        )
        V20CredProposal.deserialize(obj)

    async def test_serialize(self):
        """Test serialization."""

        cred_proposal = V20CredProposal(
            comment="Hello World",
            credential_preview=TEST_PREVIEW,
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(TEST_INDY_FILTER, ident="indy")
            ],
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("@id")

        assert cred_proposal_dict == {
            "@type": DIDCommPrefix.qualify_current(CRED_20_PROPOSAL),
            "comment": "Hello World",
            "credential_preview": {
                "@type": DIDCommPrefix.qualify_current(CRED_20_PREVIEW),
                "attributes": [
                    {"name": "test", "value": "123"},
                    {"name": "hello", "value": "world"},
                    {"name": "icon", "mime-type": "image/png", "value": "cG90YXRv"},
                ],
            },
            "formats": [
                {
                    "attach_id": "indy",
                    "format": ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                }
            ],
            "filters~attach": [
                {
                    "@id": "indy",
                    "mime-type": "application/json",
                    "data": {
                        "base64": (
                            "eyJzY2hlbWFfaWQiOiAiR01tNHZNdzhMTHJMSmpw"
                            "ODFrUlJMcDoyOmFob3k6MTU2MDM2NDAwMy4wIiwg"
                            "ImNyZWRfZGVmX2lkIjogIkdNbTR2TXc4TExyTEpq"
                            "cDgxa1JSTHA6MzpDTDoxMjp0YWcifQ=="
                        )
                    },
                }
            ],
        }

    async def test_serialize_minimal(self):
        """Test serialization."""

        cred_proposal = V20CredProposal(
            credential_preview=None,
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[AttachDecorator.data_base64({}, ident="indy")],
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("@id")

        assert cred_proposal_dict == {
            "@type": DIDCommPrefix.qualify_current(CRED_20_PROPOSAL),
            "filters~attach": [
                {
                    "@id": "indy",
                    "mime-type": "application/json",
                    "data": {"base64": "e30="},
                }
            ],
            "formats": [
                {
                    "attach_id": "indy",
                    "format": ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                }
            ],
        }


class TestV20CredProposalSchema(AsyncTestCase):
    """Test credential proposal schema."""

    async def test_make_model(self):
        """Test making model."""
        cred_proposal = V20CredProposal(
            credential_preview=TEST_PREVIEW,
            formats=[
                V20CredFormat(
                    attach_id="indy",
                    format_=ATTACHMENT_FORMAT[CRED_20_PROPOSAL][
                        V20CredFormat.Format.INDY.api
                    ],
                )
            ],
            filters_attach=[
                AttachDecorator.data_base64(TEST_INDY_FILTER, ident="indy")
            ],
        )

        data = cred_proposal.serialize()
        model_instance = V20CredProposal.deserialize(data)
        assert isinstance(model_instance, V20CredProposal)
