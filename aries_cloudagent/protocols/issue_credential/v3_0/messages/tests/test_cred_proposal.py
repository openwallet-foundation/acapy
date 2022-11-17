from asynctest import TestCase as AsyncTestCase

from aries_cloudagent.protocols.issue_credential.v3_0.messages.cred_body import (
    V30CredBody,
)

from ......messaging.decorators.attach_decorator_didcomm_v2_cred import AttachDecorator
from ......messaging.models.base import BaseModelError

from .....didcomm_prefix import DIDCommPrefix

from ...message_types import ATTACHMENT_FORMAT, CRED_30_PREVIEW, CRED_30_PROPOSAL

from ..cred_format import V30CredFormat
from ..cred_proposal import V30CredProposal, V30CredFormat
from ..inner.cred_preview import V30CredAttrSpec, V30CredPreview, V30CredPreviewBody


TEST_PREVIEW = V30CredPreview(
    _body=V30CredPreviewBody(
        attributes=(
            V30CredAttrSpec.list_plain({"test": "123", "hello": "world"})
            + [V30CredAttrSpec(name="icon", value="cG90YXRv", mime_type="image/png")]
        )
    )
)

TEST_INDY_FILTER = {
    "schema_id": "GMm4vMw8LLrLJjp81kRRLp:2:ahoy:1560364003.0",
    "cred_def_id": "GMm4vMw8LLrLJjp81kRRLp:3:CL:12:tag",
}


class TestV30CredProposal(AsyncTestCase):
    """Credential proposal tests."""

    async def test_init(self):
        """Test initializer."""
        cred_proposal = V30CredProposal(
            _body=V30CredBody(comment="Hello World", credential_preview=TEST_PREVIEW),
            attachments=[
                AttachDecorator.data_base64(
                    TEST_INDY_FILTER,
                    ident="indy",
                    format=V30CredFormat(
                        format_=ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                )
            ],
        )

        print("wow")
        print(cred_proposal)
        assert cred_proposal._body.credential_preview == TEST_PREVIEW
        assert cred_proposal._type == DIDCommPrefix.qualify_current(CRED_30_PROPOSAL)

    async def test_attachment_no_target_format(self):
        """Test attachment behaviour for only unknown formats."""

        x_cred_proposal = V30CredProposal(
            _body=V30CredBody(comment="Test"),
            attachments=[
                AttachDecorator.data_base64(
                    ident="not_indy",
                    mapping=TEST_PREVIEW.serialize(),
                    format=V30CredFormat(format_="not_indy"),
                )
            ],
        )
        assert x_cred_proposal.attachment() is None

    async def test_deserialize(self):
        """Test deserialization."""
        obj = {
            "type": "https://didcomm.org/issue-credential/3.0/propose-credential",
            "id": "56dfd607-e03b-4175-8e36-c49329da891b",
            "body": {
                "comment": "Hello World",
                "credential_preview": {
                    "type": "https://didcomm.org/issue-credential/3.0/credential-preview",
                    "body": {
                        "attributes": [
                            {"name": "test", "value": "123"},
                            {"name": "hello", "value": "world"},
                            {
                                "name": "icon",
                                "mime-type": "image/png",
                                "value": "cG90YXRv",
                            },
                        ]
                    },
                },
            },
            "attachments": [
                {
                    "id": "indy",
                    "media-type": "application/json",
                    "data": {
                        "base64": (
                            "eyJzY2hlbWFfaWQiOiAiR01tNHZNdzhMTHJMSmpw"
                            "ODFrUlJMcDoyOmFob3k6MTU2MDM2NDAwMy4wIiwg"
                            "ImNyZWRfZGVmX2lkIjogIkdNbTR2TXc4TExyTEpq"
                            "cDgxa1JSTHA6MzpDTDoxMjp0YWcifQ=="
                        )
                    },
                    "format": ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                        V30CredFormat.Format.INDY.api
                    ],
                }
            ],
        }
        cred_proposal = V30CredProposal.deserialize(obj)
        assert type(cred_proposal) == V30CredProposal

        obj["attachments"][0]["data"]["base64"] = "eyJub3QiOiAiaW5keSJ9"  # not indy
        with self.assertRaises(BaseModelError):
            V30CredProposal.deserialize(obj)

        obj["attachments"][0]["id"] = "xxx"
        with self.assertRaises(BaseModelError):
            V30CredProposal.deserialize(obj)

        obj["attachments"].append(  # more attachments than formats
            {
                "id": "def",
                "media-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                "format": "",
            }
        )
        with self.assertRaises(BaseModelError):
            V30CredProposal.deserialize(obj)

        obj = cred_proposal.serialize()
        obj["attachments"].append(
            {
                "id": "not_indy",
                "media-type": "application/json",
                "data": {"base64": "eyJub3QiOiAiaW5keSJ9"},
                "format": "<V30CredFormat(format_='not_indy')>",
            }
        )
        V30CredProposal.deserialize(obj)

    async def test_serialize(self):
        """Test serialization."""

        cred_proposal = V30CredProposal(
            _body=V30CredBody(comment="Hello World", credential_preview=TEST_PREVIEW),
            attachments=[
                AttachDecorator.data_base64(
                    TEST_INDY_FILTER,
                    ident="indy",
                    format=V30CredFormat(
                        format_=ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                )
            ],
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("id")
        print(cred_proposal_dict)

        assert cred_proposal_dict == {
            "type": DIDCommPrefix.qualify_current(CRED_30_PROPOSAL),
            "body": {
                "comment": "Hello World",
                "credential_preview": {
                    "type": "issue-credential/3.0/credential-preview",
                    "body": {
                        "attributes": [
                            {"name": "test", "value": "123"},
                            {"name": "hello", "value": "world"},
                            {
                                "name": "icon",
                                "media-type": "image/png",
                                "value": "cG90YXRv",
                            },
                        ],
                    },
                },
            },
            "attachments": [
                {
                    "id": "indy",
                    "media-type": "application/json",
                    "data": {
                        "base64": (
                            "eyJzY2hlbWFfaWQiOiAiR01tNHZNdzhMTHJMSmpw"
                            "ODFrUlJMcDoyOmFob3k6MTU2MDM2NDAwMy4wIiwg"
                            "ImNyZWRfZGVmX2lkIjogIkdNbTR2TXc4TExyTEpq"
                            "cDgxa1JSTHA6MzpDTDoxMjp0YWcifQ=="
                        )
                    },
                    "format": ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                        V30CredFormat.Format.INDY.api
                    ],
                }
            ],
        }

    async def test_serialize_minimal(self):
        """Test serialization."""

        cred_proposal = V30CredProposal(
            _body=V30CredBody(credential_preview=None),
            attachments=[
                AttachDecorator.data_base64(
                    {},
                    ident="indy",
                    format=V30CredFormat(
                        format_=ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                )
            ],
        )

        cred_proposal_dict = cred_proposal.serialize()
        cred_proposal_dict.pop("id")

        assert cred_proposal_dict == {
            "type": DIDCommPrefix.qualify_current(CRED_30_PROPOSAL),
            "body": {},
            "attachments": [
                {
                    "id": "indy",
                    "media-type": "application/json",
                    "data": {"base64": "e30="},
                    "format": ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                        V30CredFormat.Format.INDY.api
                    ],
                }
            ],
        }


class TestV30CredProposalSchema(AsyncTestCase):
    """Test credential proposal schema."""

    async def test_make_model(self):
        """Test making model."""
        cred_proposal = V30CredProposal(
            _body=V30CredBody(credential_preview=TEST_PREVIEW),
            attachments=[
                AttachDecorator.data_base64(
                    TEST_INDY_FILTER,
                    ident="indy",
                    format=V30CredFormat(
                        format_=ATTACHMENT_FORMAT[CRED_30_PROPOSAL][
                            V30CredFormat.Format.INDY.api
                        ],
                    ),
                )
            ],
        )

        data = cred_proposal.serialize()
        model_instance = V30CredProposal.deserialize(data)
        assert isinstance(model_instance, V30CredProposal)
