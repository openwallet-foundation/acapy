"""A presentation preview inner object."""


from datetime import datetime, timezone
from uuid import uuid4
from typing import Mapping

import base64

from marshmallow import fields, validate

from ......messaging.util import str_to_epoch
from .....models.base import BaseModel, BaseModelSchema
from .....valid import INDY_CRED_DEF_ID, INDY_PREDICATE, INDY_ISO8601_DATETIME
from ...message_types import PRESENTATION_PREVIEW
from ..util.indy import canon, Predicate


class PresentationAttrPreview(BaseModel):
    """Class representing an `"attributes"` attibute within the preview."""

    DEFAULT_META = {"mime-type": "text/plain"}

    class Meta:
        """Attribute preview metadata."""

        schema_class = "PresentationAttrPreviewSchema"

    def __init__(
            self,
            *,
            value: str = None,
            encoding: str = None,
            mime_type: str = None,
            **kwargs):
        """
        Initialize attribute preview object.

        Args:
            mime_type: MIME type
            encoding: encoding (omit or "base64")
            value: attribute value

        """
        super().__init__(**kwargs)
        self.value = value
        self.encoding = encoding.lower() if encoding else None
        self.mime_type = (
            mime_type.lower()
            if mime_type and mime_type != PresentationAttrPreview.DEFAULT_META.get(
                "mime-type"
            )
            else None
        )

    @staticmethod
    def list_plain(plain: dict):
        """
        Return a list of `PresentationAttrPreview` for plain text from names/values.

        Args:
            plain: dict mapping names to values

        Returns:
            PresentationAttrPreview on name/values pairs with default MIME type

        """
        return [PresentationAttrPreview(name=k, value=plain[k]) for k in plain]

    def void(self):
        """Remove value, encoding, MIME type for use in proof request."""

        self.value = None
        self.encoding = None
        self.mime_type = None

    def b64_decoded_value(self) -> str:
        """Value, base64-decoded if applicable."""

        return base64.b64decode(self.value.encode()).decode(
        ) if (
            self.value and
            self.encoding and
            self.encoding.lower() == "base64"
        ) else self.value

    def __eq__(self, other):
        """Equality comparator."""

        if all(
            getattr(self, attr, PresentationAttrPreview.DEFAULT_META.get(attr)) ==
            getattr(other, attr, PresentationAttrPreview.DEFAULT_META.get(attr))
            for attr in vars(self)
        ):
            return True  # all attrs exactly match

        if (
            self.mime_type or "text/plain"
        ).lower() != (other.mime_type or "text/plain").lower():
            return False  # distinct MIME types

        return self.b64_decoded_value() == other.b64_decoded_value()


class PresentationAttrPreviewSchema(BaseModelSchema):
    """Attribute preview schema."""

    class Meta:
        """Attribute preview schema metadata."""

        model_class = PresentationAttrPreview

    value = fields.Str(
        description="Attribute value",
        required=False
    )
    mime_type = fields.Str(
        description="MIME type (default text/plain)",
        required=False,
        data_key="mime-type",
        example="text/plain"
    )
    encoding = fields.Str(
        description="Encoding (specify base64 or omit for none)",
        required=False,
        example="base64",
        validate=validate.Equal("base64", error="Must be absent or equal to {other}")
    )


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
        attributes: Mapping[str, Mapping[str, PresentationAttrPreview]],
        predicates: Mapping[str, Mapping[str, Mapping[str, int]]],
        non_revocation_times: Mapping[str, datetime],
        **kwargs
    ):
        """
        Initialize presentation preview object.

        Args:
            _type: formalism for Marshmallow model creation: ignored
            attributes: nested dict mapping cred def identifiers to attribute names
                to attribute previews
            predicates: nested dict mapping cred def identifiers to predicates
                to predicate previews
            non_revocation_times: dict mapping cred def identifiers to non-revocation
                timestamps
        """
        super().__init__(**kwargs)
        self.attributes = attributes
        self.predicates = predicates
        self.non_revocation_times = non_revocation_times

    @staticmethod
    def from_indy_proof_request(indy_proof_request: dict):
        """Reverse-engineer presentation preview from indy proof request."""

        def do_non_revo(cd_id: str, proof_req_non_revo: dict):
            """Set non-revocation times per cred def id given from/to specifiers."""

            nonlocal non_revocation_times
            if proof_req_non_revo:
                if cd_id not in non_revocation_times:
                    non_revocation_times[cd_id] = {
                        "from": datetime.fromtimestamp(
                            proof_req_non_revo["from"],
                            tz=timezone.utc
                        ),
                        "to": datetime.fromtimestamp(
                            proof_req_non_revo["to"],
                            tz=timezone.utc
                        )
                    }
                else:
                    non_revocation_times[cd_id] = {
                        "from": max(
                            datetime.fromtimestamp(
                                proof_req_non_revo["from"],
                                tz=timezone.utc
                            ),
                            non_revocation_times[cd_id]["from"]
                        ),
                        "to": min(
                            datetime.fromtimestamp(
                                proof_req_non_revo["to"],
                                tz=timezone.utc
                            ),
                            non_revocation_times[cd_id]["to"]
                        )
                    }

        attributes = {}
        predicates = {}
        non_revocation_times = {}

        for (uuid, attr_spec) in indy_proof_request["requested_attributes"].items():
            cd_id = attr_spec["restrictions"][0]["cred_def_id"]
            if cd_id not in attributes:
                attributes[cd_id] = {}
            attributes[cd_id][attr_spec["name"]] = PresentationAttrPreview()
            do_non_revo(cd_id, attr_spec.get("non_revoked"))

        for (uuid, pred_spec) in indy_proof_request["requested_predicates"].items():
            cd_id = pred_spec["restrictions"][0]["cred_def_id"]
            if cd_id not in predicates:
                predicates[cd_id] = {}
            pred_type = pred_spec["p_type"]
            if pred_type not in predicates[cd_id]:
                predicates[cd_id][pred_type] = {}
            predicates[cd_id][pred_type][pred_spec["name"]] = (
                pred_spec["p_value"]
            )
            do_non_revo(cd_id, pred_spec.get("non_revoked"))

        return PresentationPreview(
            attributes=attributes,
            predicates=predicates,
            non_revocation_times={
                cd_id: (
                    non_revocation_times[cd_id]["to"].isoformat(" ", "seconds")
                ) for cd_id in non_revocation_times
            }
        )

    def void_attribute_previews(self):
        """Clear attribute values, encodings, MIME types from presentation preview."""
        for cd_id in self.attributes:
            for attr in self.attributes[cd_id]:
                self.attributes[cd_id][attr].void()

        return self

    @property
    def _type(self):
        """Accessor for message type."""

        return PresentationPreview.Meta.message_type

    def attr_dict(self, decode: bool = False):
        """
        Return dict mapping cred def id to name:value pair per attribute.

        Args:
            decode: whether first to decode attributes marked as having encoding

        """

        def b64(attr_prev: PresentationAttrPreview, b64deco: bool = False) -> str:
            """Base64 decode attribute value if applicable."""
            return (
                base64.b64decode(attr_prev.value.encode()).decode()
                if (
                    attr_prev.value and
                    attr_prev.encoding and
                    attr_prev.encoding == "base64" and
                    b64deco
                ) else attr_prev.value
            )

        return {
            cd_id: {
                attr: b64(self.attributes[cd_id][attr], decode)
                for attr in self.attributes[cd_id]
            } for cd_id in self.attributes
        }

    def attr_metadata(self):
        """Return nested dict mapping cred def id to attr to MIME type and encoding."""

        return {
            cd_id: {
                attr: {
                    **{
                        "mime-type": aprev.mime_type
                        for aprev in [self.attributes[cd_id][attr]] if aprev.mime_type
                    },
                    **{
                        "encoding": aprev.encoding
                        for aprev in [self.attributes[cd_id][attr]] if aprev.encoding
                    }
                } for attr in self.attributes[cd_id]
            } for cd_id in self.attributes
        }

    def indy_proof_request(
        self,
        name: str = None,
        version: str = None,
        nonce: str = None
    ) -> dict:
        """
        Return indy proof request corresponding to presentation preview.

        Args:
            name: for proof request
            version: version for proof request
            nonce: nonce for proof request

        Returns:
            Indy proof request dict.

        """
        proof_req = {
            "name": name or "proof-request",
            "version": version or "1.0",
            "nonce": nonce or str(uuid4().int),
            "requested_attributes": {},
            "requested_predicates": {}
        }
        cd_ids = []  # map ordinal to cred def id for use in proof req referents

        for (cd_id, attr_dict) in self.attr_dict().items():
            cd_ids.append(cd_id)
            cd_id_index = len(cd_ids) - 1
            for (attr, attr_value) in attr_dict.items():
                proof_req["requested_attributes"][
                    f"{cd_id_index}_{canon(attr)}_uuid"
                ] = {
                    "name": attr,
                    "restrictions": [
                        {"cred_def_id": cd_id}
                    ],
                    **{
                        "non_revoked": {
                            "from": str_to_epoch(self.non_revocation_times[cd_id]),
                            "to": str_to_epoch(self.non_revocation_times[cd_id])
                        } for _ in [""] if cd_id in self.non_revocation_times
                    }
                }

        # predicates: Mapping[str, Mapping[str, Mapping[str, str]]],
        for (cd_id, pred_dict) in self.predicates.items():
            if cd_id not in cd_ids:
                cd_ids.append(cd_id)
            cd_id_index = cd_ids.index(cd_id)
            for (pred_math, pred_attr_dict) in pred_dict.items():
                for (attr, threshold) in pred_attr_dict.items():
                    proof_req["requested_predicates"][
                        "{}_{}_{}_uuid".format(
                            cd_id_index,
                            canon(attr),
                            Predicate.get(pred_math).value.fortran
                        )
                    ] = {
                        "name": attr,
                        "p_type": pred_math,
                        "p_value": threshold,
                        "restrictions": [
                            {"cred_def_id": cd_id}
                        ],
                        **{
                            "non_revoked": {
                                "from": str_to_epoch(self.non_revocation_times[cd_id]),
                                "to": str_to_epoch(self.non_revocation_times[cd_id])
                            } for _ in [""] if cd_id in self.non_revocation_times
                        }
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
            PRESENTATION_PREVIEW,
            error="Must be absent or equal to {other}"
        )
    )
    attributes = fields.Dict(
        description=(
            "Nested object mapping cred def identifiers to attribute preview specifiers"
        ),
        required=True,
        keys=fields.Str(**INDY_CRED_DEF_ID),  # marshmallow/apispec v3.0rc3 ignores
        values=fields.Dict(
            description="Object mapping attribute names to attribute previews",
            keys=fields.Str(example="attr_name"),  # marshmallow/apispec v3.0rc3 ignores
            values=fields.Nested(PresentationAttrPreviewSchema)
        )
    )
    predicates = fields.Dict(
        description=(
            "Nested object mapping cred def identifiers to predicate preview specifiers"
        ),
        required=True,
        keys=fields.Str(**INDY_CRED_DEF_ID),
        values=fields.Dict(
            description=(
                "Nested Object mapping predicates "
                '(currently, only ">=" for 32-bit integers) '
                "to attribute names to threshold values"
            ),
            keys=fields.Str(**INDY_PREDICATE),  # marshmallow/apispec v3.0rc3 ignores
            values=fields.Dict(
                description="Object mapping attribute names to threshold values",
                keys=fields.Str(example="attr_name"),
                values=fields.Int()
            )
        )
    )
    non_revocation_times = fields.Dict(
        description=(
            "Object mapping cred def identifiers to ISO-8601 datetimes, each marking a "
            "non-revocation timestamp for its corresponding credential in the proof"
        ),
        required=False,
        default={},
        keys=fields.Str(**INDY_CRED_DEF_ID),  # marshmallow/apispec v3.0rc3 ignores
        values=fields.Str(**INDY_ISO8601_DATETIME)
    )
