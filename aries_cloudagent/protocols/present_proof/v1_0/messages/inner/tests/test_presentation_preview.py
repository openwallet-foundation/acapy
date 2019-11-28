from copy import deepcopy
from datetime import datetime, timezone
from unittest import TestCase

import json

from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock

import pytest

from .......holder.indy import IndyHolder
from .......messaging.util import canon, str_to_datetime, str_to_epoch

from ....message_types import PRESENTATION_PREVIEW
from ....util.indy import Predicate

from ..presentation_preview import (
    PresAttrSpec,
    PresPredSpec,
    PresentationPreview,
)


NOW_8601 = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(" ", "seconds")
NOW_EPOCH = str_to_epoch(NOW_8601)
S_ID = "NcYxiDXkpYi6ov5FcYDi1e:2:vidya:1.0"
CD_ID = f"NcYxiDXkpYi6ov5FcYDi1e:3:CL:{S_ID}:tag1"
PRES_PREVIEW = PresentationPreview(
    attributes=[
        PresAttrSpec(
            name="player",
            cred_def_id=CD_ID,
            value="Richie Knucklez"
        ),
        PresAttrSpec(
            name="screenCapture",
            cred_def_id=CD_ID,
            mime_type="image/png",
            value="aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl"
        )
    ],
    predicates=[
        PresPredSpec(
            name="highScore",
            cred_def_id=CD_ID,
            predicate=">=",
            threshold=1000000
        )
    ]
)
INDY_PROOF_REQ = json.loads(f"""{{
    "name": "proof-req",
    "version": "1.0",
    "nonce": "12345",
    "requested_attributes": {{
        "0_player_uuid": {{
            "name": "player",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID}"
                }}
            ]
        }},
        "0_screencapture_uuid": {{
            "name": "screenCapture",
            "restrictions": [
                {{
                    "cred_def_id": "{CD_ID}"
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
                    "cred_def_id": "{CD_ID}"
                }}
            ]
        }}
    }}
}}""")


class TestPresAttrSpec(TestCase):
    """Presentation-preview attribute specification tests"""

    def test_posture(self):
        self_attested = PresAttrSpec(
            name="ident",
            cred_def_id=None,
            value="655321"
        )
        assert self_attested.posture == PresAttrSpec.Posture.SELF_ATTESTED

        revealed = PresAttrSpec(
            name="ident",
            cred_def_id=CD_ID,
            value="655321"
        )
        assert revealed.posture == PresAttrSpec.Posture.REVEALED_CLAIM

        unrevealed = PresAttrSpec(
            name="ident",
            cred_def_id=CD_ID
        )
        assert unrevealed.posture == PresAttrSpec.Posture.UNREVEALED_CLAIM

        no_posture = PresAttrSpec(name="no_spec")
        assert no_posture.posture is None

    def test_list_plain(self):
        by_list = PresAttrSpec.list_plain(
            plain={
                "ident": "655321",
                " Given Name ": "Alexander DeLarge"
            },
            cred_def_id=CD_ID
        )
        explicit = [
            PresAttrSpec(
                name="ident",
                cred_def_id=CD_ID,
                value="655321"
            ),
            PresAttrSpec(
                name="givenname",
                cred_def_id=CD_ID,
                value="Alexander DeLarge"
            )
        ]

        # order could be askew
        for listp in by_list:
            assert any(xp == listp for xp in explicit)
        assert len(explicit) == len(by_list)

    def test_eq(self):
        attr_specs_none_plain = [
            PresAttrSpec(
                name="name",
                value="value"
            ),
            PresAttrSpec(
                name="name",
                value="value",
                mime_type=None
            ),
            PresAttrSpec(
                name=" NAME ",
                value="value"
            )
        ]
        attr_specs_different = [
            PresAttrSpec(
                name="name",
                value="dmFsdWU=",
                mime_type="image/png"
            ),
            PresAttrSpec(
                name="name",
                value="value",
                cred_def_id="cred_def_id"
            ),
            PresAttrSpec(
                name="name",
                value="distinct value",
                mime_type=None
            ),
            PresAttrSpec(
                name="distinct name",
                value="value",
                mime_type=None
            ),
            PresAttrSpec(
                name="name",
                value="dmFsdWU=",
                mime_type=None
            ),
            PresAttrSpec(name="name")
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
        dump = json.dumps({
            "name": "PLAYER",
            "cred_def_id": CD_ID,
            "value": "Richie Knucklez"
        })

        attr_spec = PresAttrSpec.deserialize(dump)
        assert type(attr_spec) == PresAttrSpec
        assert attr_spec.name == "player"

    def test_serialize(self):
        """Test serialization."""

        attr_spec_dict = PRES_PREVIEW.attributes[0].serialize()
        assert attr_spec_dict == {
            "name": "player",
            "cred_def_id": CD_ID,
            "value": "Richie Knucklez"
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
        dump = json.dumps({
            "name": "HIGH SCORE",
            "cred_def_id": CD_ID,
            "predicate": ">=",
            "threshold": 1000000
        })

        pred_spec = PresPredSpec.deserialize(dump)
        assert type(pred_spec) == PresPredSpec
        assert pred_spec.name == "highscore"

    def test_serialize(self):
        """Test serialization."""

        pred_spec_dict = PRES_PREVIEW.predicates[0].serialize()
        assert pred_spec_dict == {
            "name": "highscore",
            "cred_def_id": CD_ID,
            "predicate": ">=",
            "threshold": 1000000
        }

    def test_eq(self):
        """Test equality operator."""

        pred_spec_a = PresPredSpec(
            name="a",
            cred_def_id=CD_ID,
            predicate=Predicate.GE.value.math,
            threshold=0,
        )
        pred_spec_b = PresPredSpec(
            name="b",
            cred_def_id=CD_ID,
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


@pytest.mark.indy
class TestPresentationPreviewAsync(AsyncTestCase):
    """Presentation preview tests"""

    @pytest.mark.asyncio
    async def test_to_indy_proof_request(self):
        """Test presentation preview to indy proof request."""

        CANON_INDY_PROOF_REQ = deepcopy(INDY_PROOF_REQ)
        for spec in CANON_INDY_PROOF_REQ["requested_attributes"].values():
            spec["name"] = canon(spec["name"])
        for spec in CANON_INDY_PROOF_REQ["requested_predicates"].values():
            spec["name"] = canon(spec["name"])

        pres_preview = deepcopy(PRES_PREVIEW)

        indy_proof_req = await pres_preview.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        )

        assert indy_proof_req == CANON_INDY_PROOF_REQ

    async def test_to_indy_proof_request_self_attested(self):
        """Test presentation preview to inty proof request with self-attested values."""

        pres_preview_selfie = deepcopy(PRES_PREVIEW)
        for attr_spec in pres_preview_selfie.attributes:
            attr_spec.cred_def_id=None

        indy_proof_req_selfie = await pres_preview_selfie.indy_proof_request(
            **{k: INDY_PROOF_REQ[k] for k in ("name", "version", "nonce")}
        )

        assert not any(
            "restrictions" in attr_spec
            for attr_spec in indy_proof_req_selfie["requested_attributes"].values()
        )

    @pytest.mark.asyncio
    async def test_satisfaction(self):
        """Test presentation preview predicate satisfaction."""

        pred_spec = PresPredSpec(
            name="highScore",
            cred_def_id=CD_ID,
            predicate=Predicate.GE.value.math,
            threshold=1000000
        )
        attr_spec = PresAttrSpec(
            name="HIGHSCORE",
            cred_def_id=CD_ID,
            value=1234567
        )
        assert attr_spec.satisfies(pred_spec)

        attr_spec = PresAttrSpec(
            name="HIGHSCORE",
            cred_def_id=CD_ID,
            value=985260
        )
        assert not attr_spec.satisfies(pred_spec)


@pytest.mark.indy
class TestPresentationPreview(TestCase):
    """Presentation preview tests"""

    def test_init(self):
        """Test initializer."""
        assert PRES_PREVIEW.attributes
        assert PRES_PREVIEW.predicates

    def test_type(self):
        """Test type."""
        assert PRES_PREVIEW._type == PRESENTATION_PREVIEW

    def test_deserialize(self):
        """Test deserialization."""
        dump = {
            "@type": PRESENTATION_PREVIEW,
            "attributes": [
                {
                    "name": "player",
                    "cred_def_id": CD_ID,
                    "value": "Richie Knucklez"
                },
                {
                    "name": "screencapture",
                    "cred_def_id": CD_ID,
                    "mime-type": "image/png",
                    "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl"
                }
            ],
            "predicates": [
                {
                    "name": "highscore",
                    "cred_def_id": CD_ID,
                    "predicate": ">=",
                    "threshold": 1000000
                }
            ]
        }

        preview = PresentationPreview.deserialize(dump)
        assert type(preview) == PresentationPreview

    def test_serialize(self):
        """Test serialization."""

        preview_dict = PRES_PREVIEW.serialize()
        assert preview_dict == {
            "@type": PRESENTATION_PREVIEW,
            "attributes": [
                {
                    "name": "player",
                    "cred_def_id": CD_ID,
                    "value": "Richie Knucklez"
                },
                {
                    "name": "screencapture",
                    "cred_def_id": CD_ID,
                    "mime-type": "image/png",
                    "value": "aW1hZ2luZSBhIHNjcmVlbiBjYXB0dXJl"
                }
            ],
            "predicates": [
                {
                    "name": "highscore",
                    "cred_def_id": CD_ID,
                    "predicate": ">=",
                    "threshold": 1000000
                }
            ]
        }

    def test_eq(self):
        pres_preview_a = PresentationPreview.deserialize(PRES_PREVIEW.serialize())
        assert pres_preview_a == PRES_PREVIEW

        pres_preview_a.predicates = []
        assert pres_preview_a != PRES_PREVIEW
