import json
import pytest

from copy import deepcopy
from time import time
from unittest import TestCase

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

from .......messaging.util import canon
from .......revocation.models.indy import NonRevocationInterval

from ......didcomm_prefix import DIDCommPrefix

from ....message_types import PRESENTATION_PREVIEW
from ....util.predicate import Predicate

from ..presentation_preview import (
    PresAttrSpec,
    PresPredSpec,
    PresentationPreview,
)


S_ID = {
    "score": "NcYxiDXkpYi6ov5FcYDi1e:2:score:1.0",
    "membership": "NcYxiDXkpYi6ov5FcYDi1e:2:membership:1.0",
}
CD_ID = {name: f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID[name]}:tag1" for name in S_ID}
PRES_PREVIEW = PresentationPreview(
    attributes=[
        PresAttrSpec(
            name="player", cred_def_id=CD_ID["score"], value="Richie Knucklez"
        ),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID["score"],
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
        ),
    ],
    predicates=[
        PresPredSpec(
            name="highScore",
            cred_def_id=CD_ID["score"],
            predicate=">=",
            threshold=1000000,
        )
    ],
)
PRES_PREVIEW_ATTR_NAMES = PresentationPreview(
    attributes=[
        PresAttrSpec(
            name="player",
            cred_def_id=CD_ID["score"],
            value="Richie Knucklez",
            referent="reft-0",
        ),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID["score"],
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
            referent="reft-0",
        ),
        PresAttrSpec(
            name="member",
            cred_def_id=CD_ID["membership"],
            value="Richard Hand",
            referent="reft-1",
        ),
        PresAttrSpec(
            name="since",
            cred_def_id=CD_ID["membership"],
            value="2020-01-01",
            referent="reft-1",
        ),
    ]
)
INDY_PROOF_REQ = json.loads(
    f"""{{
    "name": "proof-req",
    "version": "1.0",
    "nonce": "12345",
    "requested_attributes": {{
        "0_player_uuid": {{
            "name": "player",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID['score']}"
                }}
            ]
        }},
        "1_screencapture_uuid": {{
            "name": "screenCapture",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID['score']}"
                }}
            ]
        }}
    }},
    "requested_predicates": {{
        "0_highscore_GE_uuid": {{
            "name": "highScore",
            "p_type": ">=",
            "p_value": 1000000,
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID['score']}"
                }}
            ]
        }}
    }}
}}"""
)
INDY_PROOF_REQ_ATTR_NAMES = json.loads(
    f"""{{
    "name": "proof-req",
    "version": "1.0",
    "nonce": "12345",
    "requested_attributes": {{
        "0_player_uuid": {{
            "names": ["player", "screenCapture"],
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID['score']}"
                }}
            ]
        }},
        "1_member_uuid": {{
            "names": ["member", "since"],
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID['membership']}"
                }}
            ]
        }}
    }},
    "requested_predicates": {{}}
}}"""
)


class TestPresAttrSpec(TestCase):
    """Presentation-preview attribute specification tests"""

    def test_posture(self):
        self_attested = PresAttrSpec(name="ident", cred_def_id=None, value="655321")
        assert self_attested.posture == PresAttrSpec.Posture.SELF_ATTESTED

        revealed = PresAttrSpec(
            name="ident", cred_def_id=CD_ID["score"], value="655321"
        )
        assert revealed.posture == PresAttrSpec.Posture.REVEALED_CLAIM

        unrevealed = PresAttrSpec(name="ident", cred_def_id=CD_ID["score"])
        assert unrevealed.posture == PresAttrSpec.Posture.UNREVEALED_CLAIM

        no_posture = PresAttrSpec(name="no_spec")
        assert no_posture.posture is None

    def test_list_plain(self):
        by_list = PresAttrSpec.list_plain(
            plain={"ident": "655321", " Given Name ": "Alexander DeLarge"},
            cred_def_id=CD_ID["score"],
        )
        explicit = [
            PresAttrSpec(name="ident", cred_def_id=CD_ID["score"], value="655321"),
            PresAttrSpec(
                name="givenname", cred_def_id=CD_ID["score"], value="Alexander DeLarge"
            ),
        ]

        # order could be askew
        for listp in by_list:
            assert any(xp == listp for xp in explicit)
        assert len(explicit) == len(by_list)

    def test_list_plain_share_referent(self):
        by_list = PresAttrSpec.list_plain(
            plain={"ident": "655321", " Given Name ": "Alexander DeLarge"},
            cred_def_id=CD_ID["score"],
            referent="dummy",
        )
        explicit = [
            PresAttrSpec(
                name="ident",
                cred_def_id=CD_ID["score"],
                value="655321",
                referent="dummy",
            ),
            PresAttrSpec(
                name="givenname",
                cred_def_id=CD_ID["score"],
                value="Alexander DeLarge",
                referent="dummy",
            ),
        ]

        # order could be askew
        for listp in by_list:
            assert any(xp == listp for xp in explicit)
        assert len(explicit) == len(by_list)

    def test_eq(self):
        attr_specs_none_plain = [
            PresAttrSpec(name="name", value="value"),
            PresAttrSpec(name="name", value="value", mime_type=None),
            PresAttrSpec(name=" NAME ", value="value"),
        ]
        attr_specs_different = [
            PresAttrSpec(name="name", value="dmFsdWU=", mime_type="image/png"),
            PresAttrSpec(name="name", value="value", cred_def_id="cred_def_id"),
            PresAttrSpec(name="name", value="distinct value", mime_type=None),
            PresAttrSpec(name="distinct name", value="value", mime_type=None),
            PresAttrSpec(name="name", value="dmFsdWU=", mime_type=None),
            PresAttrSpec(name="name"),
            PresAttrSpec(
                name="name", value="value", cred_def_id="cred_def_id", referent="reft-0"
            ),
            PresAttrSpec(
                name="name", value="value", cred_def_id="cred_def_id", referent="reft-1"
            ),
        ]

        for lhs in attr_specs_none_plain:
            for rhs in attr_specs_different:
                assert lhs != rhs

        for lidx in range(len(attr_specs_none_plain) - 1):
            for ridx in range(lidx + 1, len(attr_specs_none_plain)):
                assert attr_specs_none_plain[lidx] == attr_specs_none_plain[ridx]

        for lidx in range(len(attr_specs_different) - 1):
            for ridx in range(lidx + 1, len(attr_specs_different)):
                assert attr_specs_different[lidx] != attr_specs_different[ridx]

    def test_deserialize(self):
        """Test deserialization."""
        dump = json.dumps(
            {
                "name": "PLAYER",
                "cred_def_id": CD_ID["score"],
                "value": "Richie Knucklez",
            }
        )

        attr_spec = PresAttrSpec.deserialize(dump)
        assert type(attr_spec) == PresAttrSpec
        assert canon(attr_spec.name) == "player"

        dump = json.dumps(
            {
                "name": "PLAYER",
                "cred_def_id": CD_ID["score"],
                "value": "Richie Knucklez",
                "referent": "0",
            }
        )

        attr_spec = PresAttrSpec.deserialize(dump)
        assert type(attr_spec) == PresAttrSpec
        assert canon(attr_spec.name) == "player"

    def test_serialize(self):
        """Test serialization."""

        attr_spec_dict = PRES_PREVIEW.attributes[0].serialize()
        assert attr_spec_dict == {
            "name": "player",
            "cred_def_id": CD_ID["score"],
            "value": "Richie Knucklez",
        }

        attr_spec_dict = PRES_PREVIEW_ATTR_NAMES.attributes[0].serialize()
        assert attr_spec_dict == {
            "name": "player",
            "cred_def_id": CD_ID["score"],
            "value": "Richie Knucklez",
            "referent": "reft-0",
        }


class TestPredicate(TestCase):
    """Predicate tests for coverage"""

    def test_get(self):
        """Get predicate."""
        assert Predicate.get("LT") == Predicate.get("$lt") == Predicate.get("<")
        assert Predicate.get("LE") == Predicate.get("$lte") == Predicate.get("<=")
        assert Predicate.get("GE") == Predicate.get("$gte") == Predicate.get(">=")
        assert Predicate.get("GT") == Predicate.get("$gt") == Predicate.get(">")
        assert Predicate.get("!=") is None

    def test_cmp(self):
        """Test comparison via predicates"""
        assert Predicate.get("LT").value.yes(0, 1)
        assert Predicate.get("LT").value.yes("0", "1")
        assert Predicate.get("LT").value.no(0, 0)
        assert Predicate.get("LT").value.no(1, 0)
        assert Predicate.get("LT").value.no("1", "0")
        assert Predicate.get("LT").value.no("0", "0")

        assert Predicate.get("LE").value.yes(0, 1)
        assert Predicate.get("LE").value.yes("0", "1")
        assert Predicate.get("LE").value.yes(0, 0)
        assert Predicate.get("LE").value.no(1, 0)
        assert Predicate.get("LE").value.no("1", "0")
        assert Predicate.get("LE").value.yes("0", "0")

        assert Predicate.get("GE").value.no(0, 1)
        assert Predicate.get("GE").value.no("0", "1")
        assert Predicate.get("GE").value.yes(0, 0)
        assert Predicate.get("GE").value.yes(1, 0)
        assert Predicate.get("GE").value.yes("1", "0")
        assert Predicate.get("GE").value.yes("0", "0")

        assert Predicate.get("GT").value.no(0, 1)
        assert Predicate.get("GT").value.no("0", "1")
        assert Predicate.get("GT").value.no(0, 0)
        assert Predicate.get("GT").value.yes(1, 0)
        assert Predicate.get("GT").value.yes("1", "0")
        assert Predicate.get("GT").value.no("0", "0")


class TestPresPredSpec(TestCase):
    """Presentation predicate specification tests"""

    def test_deserialize(self):
        """Test deserialization."""
        dump = json.dumps(
            {
                "name": "HIGH SCORE",
                "cred_def_id": CD_ID["score"],
                "predicate": ">=",
                "threshold": 1000000,
            }
        )

        pred_spec = PresPredSpec.deserialize(dump)
        assert type(pred_spec) == PresPredSpec
        assert canon(pred_spec.name) == "highscore"

    def test_serialize(self):
        """Test serialization."""

        pred_spec_dict = PRES_PREVIEW.predicates[0].serialize()
        assert pred_spec_dict == {
            "name": "highScore",
            "cred_def_id": CD_ID["score"],
            "predicate": ">=",
            "threshold": 1000000,
        }

    def test_eq(self):
        """Test equality operator."""

        pred_spec_a = PresPredSpec(
            name="a",
            cred_def_id=CD_ID["score"],
            predicate=Predicate.GE.value.math,
            threshold=0,
        )
        pred_spec_b = PresPredSpec(
            name="b",
            cred_def_id=CD_ID["score"],
            predicate=Predicate.GE.value.math,
            threshold=0,
        )
        assert pred_spec_a != pred_spec_b

        pred_spec_a.name = "b"
        assert pred_spec_a == pred_spec_b

        pred_spec_a.predicate = Predicate.LE.value.math
        assert pred_spec_a != pred_spec_b

        pred_spec_a.predicate = Predicate.GE.value.math
        assert pred_spec_a == pred_spec_b

        pred_spec_a.threshold = 100
        assert pred_spec_a != pred_spec_b

        pred_spec_a.threshold = 0
        pred_spec_a.cred_def_id = None
        assert pred_spec_a != pred_spec_b


@pytest.mark.indy
class TestPresentationPreviewAsync(AsyncTestCase):
    """Presentation preview tests"""

    @pytest.mark.asyncio
    async def test_to_indy_proof_request(self):
        """Test presentation preview to indy proof request."""

        indy_proof_req = await PRES_PREVIEW.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        )

        assert indy_proof_req == INDY_PROOF_REQ

    @pytest.mark.asyncio
    async def test_to_indy_proof_request_attr_names(self):
        """Test presentation preview to indy proof request."""

        indy_proof_req = await PRES_PREVIEW_ATTR_NAMES.indy_proof_request(
            **{k: INDY_PROOF_REQ_ATTR_NAMES[k] for k in ("name", "version", "nonce")}
        )

        assert indy_proof_req == INDY_PROOF_REQ_ATTR_NAMES

    async def test_to_indy_proof_request_self_attested(self):
        """Test presentation preview to indy proof request with self-attested values."""

        pres_preview_selfie = deepcopy(PRES_PREVIEW)
        for attr_spec in pres_preview_selfie.attributes:
            attr_spec.cred_def_id = None

        indy_proof_req_selfie = await pres_preview_selfie.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        )

        assert not any(
            "restrictions" in attr_spec
            for attr_spec in indy_proof_req_selfie["requested_attributes"].values()
        )

    @pytest.mark.asyncio
    async def test_to_indy_proof_request_revo_default_interval(self):
        """Test pres preview to indy proof req with revocation support, defaults."""

        copy_indy_proof_req = deepcopy(INDY_PROOF_REQ)

        pres_preview = deepcopy(PRES_PREVIEW)
        mock_ledger = async_mock.MagicMock(
            get_credential_definition=async_mock.CoroutineMock(
                return_value={"value": {"revocation": {"...": "..."}}}
            )
        )

        indy_proof_req_revo = await pres_preview.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")},
            ledger=mock_ledger,
        )

        for uuid, attr_spec in indy_proof_req_revo["requested_attributes"].items():
            assert set(attr_spec.get("non_revoked", {}).keys()) == {"from", "to"}
            copy_indy_proof_req["requested_attributes"][uuid][
                "non_revoked"
            ] = attr_spec["non_revoked"]
        for uuid, pred_spec in indy_proof_req_revo["requested_predicates"].items():
            assert set(pred_spec.get("non_revoked", {}).keys()) == {"from", "to"}
            copy_indy_proof_req["requested_predicates"][uuid][
                "non_revoked"
            ] = pred_spec["non_revoked"]

        assert copy_indy_proof_req == indy_proof_req_revo

    @pytest.mark.asyncio
    async def test_to_indy_proof_request_revo(self):
        """Test pres preview to indy proof req with revocation support, interval."""

        EPOCH_NOW = int(time())
        copy_indy_proof_req = deepcopy(INDY_PROOF_REQ)

        pres_preview = deepcopy(PRES_PREVIEW)
        mock_ledger = async_mock.MagicMock(
            get_credential_definition=async_mock.CoroutineMock(
                return_value={"value": {"revocation": {"...": "..."}}}
            )
        )

        indy_proof_req_revo = await pres_preview.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")},
            ledger=mock_ledger,
            non_revoc_intervals={
                CD_ID[s_id]: NonRevocationInterval(1234567890, EPOCH_NOW)
                for s_id in S_ID
            },
        )

        for uuid, attr_spec in indy_proof_req_revo["requested_attributes"].items():
            assert set(attr_spec.get("non_revoked", {}).keys()) == {"from", "to"}
            copy_indy_proof_req["requested_attributes"][uuid][
                "non_revoked"
            ] = attr_spec["non_revoked"]
        for uuid, pred_spec in indy_proof_req_revo["requested_predicates"].items():
            assert set(pred_spec.get("non_revoked", {}).keys()) == {"from", "to"}
            copy_indy_proof_req["requested_predicates"][uuid][
                "non_revoked"
            ] = pred_spec["non_revoked"]

        assert copy_indy_proof_req == indy_proof_req_revo

    @pytest.mark.asyncio
    async def test_satisfaction(self):
        """Test presentation preview predicate satisfaction."""

        pred_spec = PresPredSpec(
            name="highScore",
            cred_def_id=CD_ID["score"],
            predicate=Predicate.GE.value.math,
            threshold=1000000,
        )
        attr_spec = PresAttrSpec(
            name="HIGHSCORE", cred_def_id=CD_ID["score"], value=1234567
        )
        assert attr_spec.satisfies(pred_spec)

        attr_spec = PresAttrSpec(
            name="HIGHSCORE", cred_def_id=CD_ID["score"], value=985260
        )
        assert not attr_spec.satisfies(pred_spec)


@pytest.mark.indy
class TestPresentationPreview(TestCase):
    """Presentation preview tests"""

    def test_init(self):
        """Test initializer."""
        assert PRES_PREVIEW.attributes
        assert PRES_PREVIEW.predicates
        assert PRES_PREVIEW.has_attr_spec(
            cred_def_id=CD_ID["score"], name="player", value="Richie Knucklez"
        )

    def test_type(self):
        """Test type."""
        assert PRES_PREVIEW._type == DIDCommPrefix.qualify_current(PRESENTATION_PREVIEW)

    def test_deserialize(self):
        """Test deserialization."""
        dump = {
            "@type": DIDCommPrefix.qualify_current(PRESENTATION_PREVIEW),
            "attributes": [
                {
                    "name": "player",
                    "cred_def_id": CD_ID["score"],
                    "value": "Richie Knucklez",
                },
                {
                    "name": "screenCapture",
                    "cred_def_id": CD_ID["score"],
                    "mime-type": "image/png",
                    "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                },
            ],
            "predicates": [
                {
                    "name": "highScore",
                    "cred_def_id": CD_ID["score"],
                    "predicate": ">=",
                    "threshold": 1000000,
                }
            ],
        }

        preview = PresentationPreview.deserialize(dump)
        assert type(preview) == PresentationPreview

    def test_serialize(self):
        """Test serialization."""

        preview_dict = PRES_PREVIEW.serialize()
        assert preview_dict == {
            "@type": DIDCommPrefix.qualify_current(PRESENTATION_PREVIEW),
            "attributes": [
                {
                    "name": "player",
                    "cred_def_id": CD_ID["score"],
                    "value": "Richie Knucklez",
                },
                {
                    "name": "screenCapture",
                    "cred_def_id": CD_ID["score"],
                    "mime-type": "image/png",
                    "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl",
                },
            ],
            "predicates": [
                {
                    "name": "highScore",
                    "cred_def_id": CD_ID["score"],
                    "predicate": ">=",
                    "threshold": 1000000,
                }
            ],
        }

    def test_eq(self):
        pres_preview_a = PresentationPreview.deserialize(PRES_PREVIEW.serialize())
        assert pres_preview_a == PRES_PREVIEW

        pres_preview_a.predicates = []
        assert pres_preview_a != PRES_PREVIEW
