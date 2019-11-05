"""A presentation preview inner object."""


from enum import Enum
from uuid import uuid4
from time import time
from typing import Mapping, Sequence

from marshmallow import fields, validate

from ......ledger.indy import IndyLedger
from ......messaging.models.base import BaseModel, BaseModelSchema
from ......messaging.util import canon
from ......messaging.valid import INDY_CRED_DEF_ID, INDY_PREDICATE
from ......wallet.util import b64_to_str

from ...message_types import PRESENTATION_PREVIEW
from ...util.indy import Predicate


class PresPredSpec(BaseModel):
    """Class representing a predicate specification within a presentation preview."""

    class Meta:
        """Pred spec metadata."""

        schema_class = "PresPredSpecSchema"

    def __init__(
        self, name: str, *, cred_def_id: str, predicate: str, threshold: int, **kwargs
    ):
        """
        Initialize  preview object.

        Args:
            name: attribute name
            cred_def_id: credential definition identifier
            predicate: predicate type (e.g., ">=")
            threshold: threshold value

        """
        super().__init__(**kwargs)
        self.name = canon(name)
        self.cred_def_id = cred_def_id
        self.predicate = predicate
        self.threshold = threshold

    def __eq__(self, other):
        """Equality comparator."""

        for part in vars(self):
            if getattr(self, part, None) != getattr(other, part, None):
                return False
        return True


class PresPredSpecSchema(BaseModelSchema):
    """Predicate specifiation schema."""

    class Meta:
        """Predicate specifiation schema metadata."""

        model_class = PresPredSpec

    name = fields.Str(description="Attribute name", required=True, example="high_score")
    cred_def_id = fields.Str(
        description="Credential definition identifier",
        required=True,
        **INDY_CRED_DEF_ID,
    )
    predicate = fields.Str(
        description="Predicate (currently, indy supports >=)",
        required=True,
        **INDY_PREDICATE,
    )
    threshold = fields.Int(description="Threshold value", required=True)


class PresAttrSpec(BaseModel):
    """Class representing an attibute specification within a presentation preview."""

    class Meta:
        """Attr spec metadata."""

        schema_class = "PresAttrSpecSchema"

    class Posture(Enum):
        """Attribute posture: self-attested, revealed claim or unrevealed claim."""

        SELF_ATTESTED = 0
        REVEALED_CLAIM = 1
        UNREVEALED_CLAIM = 2

    def __init__(
        self,
        name: str,
        *,
        cred_def_id: str = None,
        mime_type: str = None,
        value: str = None,
        **kwargs,
    ):
        """
        Initialize attribute specification object.

        Args:
            name: attribute name
            cred_def_id: credential definition identifier
                (None for self-attested attribute)
            mime_type: MIME type
            value: attribute value as credential stores it
                (None for unrevealed attribute)

        """
        super().__init__(**kwargs)
        self.name = canon(name)
        self.cred_def_id = cred_def_id
        self.mime_type = mime_type.lower() if mime_type else None
        self.value = value

    @staticmethod
    def list_plain(plain: dict, cred_def_id: str):
        """
        Return a list of `PresAttrSpec` on input cred def id.

        Args:
            plain: dict mapping names to values


        Returns:
            List of PresAttrSpec on input cred def id with no MIME types

        """
        return [
            PresAttrSpec(name=k, cred_def_id=cred_def_id, value=plain[k]) for k in plain
        ]

    @property
    def posture(self) -> "PresAttrSpec.Posture":
        """Attribute posture: self-attested, revealed claim, or unrevealed claim."""

        if self.cred_def_id:
            if self.value:
                return PresAttrSpec.Posture.REVEALED_CLAIM
            return PresAttrSpec.Posture.UNREVEALED_CLAIM
        if self.value:
            return PresAttrSpec.Posture.SELF_ATTESTED

        return None

    def b64_decoded_value(self) -> str:
        """Value, base64-decoded if applicable."""

        return b64_to_str(self.value) if self.value and self.mime_type else self.value

    def satisfies(self, pred_spec: PresPredSpec):
        """Whether current specified attribute satisfied input specified predicate."""

        return bool(
            self.value
            and not self.mime_type
            and self.name == pred_spec.name
            and self.cred_def_id == pred_spec.cred_def_id
            and Predicate.get(pred_spec.predicate).value.yes(
                self.value, pred_spec.threshold
            )
        )

    def __eq__(self, other):
        """Equality comparator."""

        if self.name != other.name:
            return False  # distinct attribute names (canonicalized on init)

        if self.cred_def_id != other.cred_def_id:
            return False  # distinct attribute cred def ids

        if self.mime_type != other.mime_type:
            return False  # distinct MIME types

        return self.b64_decoded_value() == other.b64_decoded_value()


class PresAttrSpecSchema(BaseModelSchema):
    """Attribute specifiation schema."""

    class Meta:
        """Attribute specifiation schema metadata."""

        model_class = PresAttrSpec

    name = fields.Str(
        description="Attribute name", required=True, example="favourite_drink"
    )
    cred_def_id = fields.Str(required=False, **INDY_CRED_DEF_ID)
    mime_type = fields.Str(
        description="MIME type (default null)",
        required=False,
        data_key="mime-type",
        example="image/jpeg",
    )
    value = fields.Str(description="Attribute value", required=False, example="martini")


class PresentationPreview(BaseModel):
    """Class representing presentation preview."""

    class Meta:
        """Presentation preview metadata."""

        schema_class = "PresentationPreviewSchema"
        message_type = PRESENTATION_PREVIEW

    def __init__(
        self,
        *,
        _type: str = None,
        attributes: Sequence[PresAttrSpec] = None,
        predicates: Sequence[PresPredSpec] = None,
        **kwargs,
    ):
        """
        Initialize presentation preview object.

        Args:
            _type: formalism for Marshmallow model creation: ignored
            attributes: list of attribute specifications
            predicates: list of predicate specifications

        """
        super().__init__(**kwargs)
        self.attributes = list(attributes) if attributes else []
        self.predicates = list(predicates) if predicates else []

    @property
    def _type(self):
        """Accessor for message type."""

        return PresentationPreview.Meta.message_type

    async def indy_proof_request(
        self,
        name: str = None,
        version: str = None,
        nonce: str = None,
        ledger: IndyLedger = None,
        timestamps: Mapping[str, int] = None,
    ) -> dict:
        """
        Return indy proof request corresponding to presentation preview.

        Typically the verifier turns the proof preview into a proof request.

        Args:
            name: for proof request
            version: version for proof request
            nonce: nonce for proof request
            ledger: ledger with credential definitions, to check for revocation support
            timestamps: dict mapping cred def ids to non-revocation
                timestamps to use (default current time where applicable)

        Returns:
            Indy proof request dict.

        """

        def non_revo(cred_def_id: str):
            """Non-revocation timestamp to use for input cred def id."""

            nonlocal epoch_now
            nonlocal timestamps

            return (timestamps or {}).get(cred_def_id, epoch_now)

        def ord_cred_def_id(cred_def_id: str):
            """Ordinal for cred def id to use in suggestive proof req referent."""

            nonlocal cred_def_ids

            if cred_def_id in cred_def_ids:
                return cred_def_ids.index(cred_def_id)
            cred_def_ids.append(cred_def_id)
            return len(cred_def_ids) - 1

        epoch_now = int(time())  # TODO: take cred_def_id->timestamp here, default now
        cred_def_ids = []

        proof_req = {
            "name": name or "proof-request",
            "version": version or "1.0",
            "nonce": nonce or str(uuid4().int),
            "requested_attributes": {},
            "requested_predicates": {},
        }

        for attr_spec in self.attributes:
            if attr_spec.posture == PresAttrSpec.Posture.SELF_ATTESTED:
                proof_req["requested_attributes"][f"{canon(attr_spec.name)}"] = {
                    "name": canon(attr_spec.name)
                }
            else:
                cd_id = attr_spec.cred_def_id
                revo_support = bool(
                    ledger
                    and await ledger.get_credential_definition(cd_id)["value"][
                        "revocation"
                    ]
                )

                timestamp = non_revo(attr_spec.cred_def_id)
                proof_req["requested_attributes"][
                    "{}_{}_uuid".format(ord_cred_def_id(cd_id), canon(attr_spec.name))
                ] = {
                    "name": canon(attr_spec.name),
                    "restrictions": [{"cred_def_id": cd_id}],
                    **{
                        "non_revoked": {"from": timestamp, "to": timestamp}
                        for _ in [""]
                        if revo_support
                    },
                }

        for pred_spec in self.predicates:
            cd_id = pred_spec.cred_def_id
            revo_support = bool(
                ledger
                and await ledger.get_credential_definition(cd_id)["value"]["revocation"]
            )

            timestamp = non_revo(attr_spec.cred_def_id)
            proof_req["requested_predicates"][
                "{}_{}_{}_uuid".format(
                    ord_cred_def_id(cd_id),
                    canon(pred_spec.name),
                    Predicate.get(pred_spec.predicate).value.fortran,
                )
            ] = {
                "name": canon(pred_spec.name),
                "p_type": pred_spec.predicate,
                "p_value": pred_spec.threshold,
                "restrictions": [{"cred_def_id": cd_id}],
                **{
                    "non_revoked": {"from": timestamp, "to": timestamp}
                    for _ in [""]
                    if revo_support
                },
            }

        return proof_req

    def __eq__(self, other):
        """Equality comparator."""

        for part in vars(self):
            if getattr(self, part, None) != getattr(other, part, None):
                return False
        return True


class PresentationPreviewSchema(BaseModelSchema):
    """Presentation preview schema."""

    class Meta:
        """Presentation preview schema metadata."""

        model_class = PresentationPreview

    _type = fields.Str(
        description="Message type identifier",
        required=False,
        example=PRESENTATION_PREVIEW,
        data_key="@type",
        validate=validate.Equal(
            PRESENTATION_PREVIEW, error="Must be absent or equal to {other}"
        ),
    )
    attributes = fields.Nested(PresAttrSpecSchema, required=True, many=True)
    predicates = fields.Nested(PresPredSpecSchema, required=True, many=True)
