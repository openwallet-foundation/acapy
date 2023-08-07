"""
A message decorator for attachments.

An attach decorator embeds content or specifies appended content.
"""


import copy
import json
import uuid
from typing import Any, Mapping, Sequence, Tuple, Union

from marshmallow import EXCLUDE, fields, pre_load

from ...did.did_key import DIDKey
from ...wallet.base import BaseWallet
from ...wallet.key_type import ED25519
from ...wallet.util import (
    b58_to_bytes,
    b64_to_bytes,
    b64_to_str,
    bytes_to_b58,
    bytes_to_b64,
    set_urlsafe_b64,
    str_to_b64,
    unpad,
)
from ..models.base import BaseModel, BaseModelError, BaseModelSchema
from ..valid import (
    BASE64_EXAMPLE,
    BASE64_VALIDATE,
    BASE64URL_NO_PAD_EXAMPLE,
    BASE64URL_NO_PAD_VALIDATE,
    INDY_ISO8601_DATETIME_EXAMPLE,
    INDY_ISO8601_DATETIME_VALIDATE,
    JWS_HEADER_KID_EXAMPLE,
    JWS_HEADER_KID_VALIDATE,
    SHA256_EXAMPLE,
    SHA256_VALIDATE,
    UUID4_EXAMPLE,
    DictOrDictListField,
)


class AttachDecoratorDataJWSHeader(BaseModel):
    """Attach decorator data JWS header."""

    class Meta:
        """AttachDecoratorDataJWS metadata."""

        schema_class = "AttachDecoratorDataJWSHeaderSchema"

    def __init__(self, kid: str):
        """Initialize JWS header to include in attach decorator data."""
        self.kid = kid

    def __eq__(self, other: Any):
        """Compare equality with another."""

        return isinstance(self, other.__class__) and self.kid == other.kid


class AttachDecoratorDataJWSHeaderSchema(BaseModelSchema):
    """Attach decorator data JWS header schema."""

    class Meta:
        """Attach decorator data schema metadata."""

        model_class = AttachDecoratorDataJWSHeader
        unknown = EXCLUDE

    kid = fields.Str(
        required=True,
        validate=JWS_HEADER_KID_VALIDATE,
        metadata={
            "description": "Key identifier, in W3C did:key or DID URL format",
            "example": JWS_HEADER_KID_EXAMPLE,
        },
    )


class AttachDecoratorData1JWS(BaseModel):
    """Single Detached JSON Web Signature for inclusion in attach decorator data."""

    class Meta:
        """AttachDecoratorData1JWS metadata."""

        schema_class = "AttachDecoratorData1JWSSchema"

    def __init__(
        self,
        *,
        header: AttachDecoratorDataJWSHeader,
        protected: str = None,
        signature: str,
    ):
        """Initialize flattened single-JWS to include in attach decorator data."""
        self.header = header
        self.protected = protected
        self.signature = signature

    def __eq__(self, other: Any):
        """Compare equality with another."""

        return (
            isinstance(self, other.__class__)
            and self.header == other.header
            and self.protected == other.protected
            and self.signature == other.signature
        )


class AttachDecoratorData1JWSSchema(BaseModelSchema):
    """Single attach decorator data JWS schema."""

    class Meta:
        """Single attach decorator data JWS schema metadata."""

        model_class = AttachDecoratorData1JWS
        unknown = EXCLUDE

    header = fields.Nested(AttachDecoratorDataJWSHeaderSchema, required=True)
    protected = fields.Str(
        required=False,
        validate=BASE64URL_NO_PAD_VALIDATE,
        metadata={
            "description": "protected JWS header",
            "example": BASE64URL_NO_PAD_EXAMPLE,
        },
    )
    signature = fields.Str(
        required=True,
        validate=BASE64URL_NO_PAD_VALIDATE,
        metadata={"description": "signature", "example": BASE64URL_NO_PAD_EXAMPLE},
    )


class AttachDecoratorDataJWS(BaseModel):
    """
    Detached JSON Web Signature for inclusion in attach decorator data.

    May hold one signature in flattened format, or multiple signatures in the
    "signatures" member.

    """

    class Meta:
        """AttachDecoratorDataJWS metadata."""

        schema_class = "AttachDecoratorDataJWSSchema"

    def __init__(
        self,
        *,
        header: AttachDecoratorDataJWSHeader = None,
        protected: str = None,
        signature: str = None,
        signatures: Sequence[AttachDecoratorData1JWS] = None,
    ):
        """Initialize JWS to include in attach decorator multi-sig data."""
        self.header = header
        self.protected = protected
        self.signature = signature
        self.signatures = signatures


class AttachDecoratorDataJWSSchema(BaseModelSchema):
    """Schema for detached JSON Web Signature for inclusion in attach decorator data."""

    class Meta:
        """Metadata for schema for detached JWS for inclusion in attach deco data."""

        model_class = AttachDecoratorDataJWS
        unknown = EXCLUDE

    @pre_load
    def validate_single_xor_multi_sig(self, data: Mapping, **kwargs):
        """Ensure model is for either 1 or many sigatures, not mishmash of both."""

        if "signatures" in data:
            if any(k in data for k in ("header", "protected", "signature")):
                raise BaseModelError(
                    "AttachDecoratorDataJWSSchema: "
                    "JWS must be flattened or general JSON serialization format"
                )
        elif not all(k in data for k in ("header", "signature")):
            raise BaseModelError(
                "AttachDecoratorDataJWSSchema: "
                "Flattened JSON serialization format must include header and signature"
            )

        return data

    header = fields.Nested(AttachDecoratorDataJWSHeaderSchema, required=False)
    protected = fields.Str(
        required=False,
        validate=BASE64URL_NO_PAD_VALIDATE,
        metadata={
            "description": "protected JWS header",
            "example": BASE64URL_NO_PAD_EXAMPLE,
        },
    )
    signature = fields.Str(
        required=False,
        validate=BASE64URL_NO_PAD_VALIDATE,
        metadata={"description": "signature", "example": BASE64URL_NO_PAD_EXAMPLE},
    )
    signatures = fields.List(
        fields.Nested(AttachDecoratorData1JWSSchema),
        required=False,
        metadata={"description": "List of signatures"},
    )


def did_key(verkey: str) -> str:
    """Qualify verkey into DID key if need be."""

    if verkey.startswith("did:key:"):
        return verkey

    return DIDKey.from_public_key_b58(verkey, ED25519).did


def raw_key(verkey: str) -> str:
    """Strip qualified key to raw key if need be."""

    if verkey.startswith("did:key:"):
        return DIDKey.from_did(verkey).public_key_b58

    return verkey


class AttachDecoratorData(BaseModel):
    """Attach decorator data."""

    class Meta:
        """AttachDecoratorData metadata."""

        schema_class = "AttachDecoratorDataSchema"

    def __init__(
        self,
        *,
        jws_: AttachDecoratorDataJWS = None,
        sha256_: str = None,
        links_: Union[Sequence[str], str] = None,
        base64_: str = None,
        json_: Union[Sequence[dict], dict] = None,
    ):
        """
        Initialize decorator data.

        Specify content for one of:

            - `base64_`
            - `json_`
            - `links_`.

        Args:
            jws_: detached JSON Web Signature over base64 or linked attachment content
            sha256_: optional sha-256 hash for content
            links_: URL or list of URLs
            base64_: base64 encoded content for inclusion
            json_: dict content for inclusion as json

        """
        if jws_:
            self.jws_ = jws_
            assert not json_

        if base64_:
            self.base64_ = base64_
        elif json_:
            # prevent external manipulation of attachment data
            self.json_ = copy.deepcopy(json_)
        else:
            assert isinstance(links_, (str, Sequence))
            self.links_ = [links_] if isinstance(links_, str) else list(links_)
        if sha256_:
            self.sha256_ = sha256_

    @property
    def base64(self):
        """Accessor for base64 decorator data, or None."""

        return getattr(self, "base64_", None)

    @property
    def jws(self):
        """Accessor for JWS, or None."""

        return getattr(self, "jws_", None)

    @property
    def signatures(self) -> int:
        """Accessor for number of signatures."""

        if self.jws:
            return 1 if self.jws.signature else len(self.jws.signatures)
        return 0

    @property
    def signed(self) -> bytes:
        """Accessor for signed content (payload), None for unsigned."""

        return (
            b64_to_bytes(unpad(set_urlsafe_b64(self.base64, urlsafe=True)))
            if self.signatures
            else None
        )

    def header_map(self, idx: int = 0, jose: bool = True) -> Mapping:
        """
        Accessor for header info at input index, default 0 or unique for singly-signed.

        Args:
            idx: index of interest, zero-based (default 0)
            jose: True to return unprotected header attributes, False for protected only

        """
        if not self.signatures:
            return None

        headers = {}
        sig = self.jws if self.jws.signature else self.jws.signatures[idx]
        if sig.protected:
            headers.update(json.loads(b64_to_str(sig.protected, urlsafe=True)))
        if jose:
            headers.update(sig.header.serialize())
        return headers

    @property
    def json(self):
        """Accessor for json decorator data, or None."""
        json_data = getattr(self, "json_", None)

        # Prevent external manipulation of attachment data
        return copy.deepcopy(json_data) if json_data else None

    @property
    def links(self):
        """Accessor for links decorator data, or None."""

        return getattr(self, "links_", None)

    @property
    def sha256(self):
        """Accessor for sha256 decorator data, or None."""

        return getattr(self, "sha256_", None)

    async def sign(
        self,
        verkeys: Union[str, Sequence[str]],
        wallet: BaseWallet,
    ):
        """
        Sign base64 data value of attachment.

        Args:
            verkeys: verkey(s) of the signing party (in raw or DID key format)
            wallet: The wallet to use for the signature

        """

        def build_protected(verkey: str):
            """Build protected header."""

            return str_to_b64(
                json.dumps(
                    {
                        "alg": "EdDSA",
                        "kid": did_key(verkey),
                        "jwk": {
                            "kty": "OKP",
                            "crv": "Ed25519",
                            "x": bytes_to_b64(
                                b58_to_bytes(raw_key(verkey)), urlsafe=True, pad=False
                            ),
                            "kid": did_key(verkey),
                        },
                    }
                ),
                urlsafe=True,
                pad=False,
            )

        assert self.base64

        b64_payload = unpad(set_urlsafe_b64(self.base64, True))

        if isinstance(verkeys, str) or (
            isinstance(verkeys, Sequence) and len(verkeys) == 1
        ):
            kid = did_key(verkeys if isinstance(verkeys, str) else verkeys[0])
            verkey = raw_key(verkeys if isinstance(verkeys, str) else verkeys[0])
            b64_protected = build_protected(verkey)
            b64_sig = bytes_to_b64(
                await wallet.sign_message(
                    message=(b64_protected + "." + b64_payload).encode("ascii"),
                    from_verkey=verkey,
                ),
                urlsafe=True,
                pad=False,
            )
            self.jws_ = AttachDecoratorDataJWS.deserialize(
                {
                    "header": AttachDecoratorDataJWSHeader(kid).serialize(),
                    "protected": b64_protected,  # always present by construction
                    "signature": b64_sig,
                }
            )
        else:
            jws = {"signatures": []}
            for verkey in verkeys:
                b64_protected = build_protected(verkey)
                b64_sig = bytes_to_b64(
                    await wallet.sign_message(
                        message=(b64_protected + "." + b64_payload).encode("ascii"),
                        from_verkey=raw_key(verkey),
                    ),
                    urlsafe=True,
                    pad=False,
                )
                jws["signatures"].append(
                    {
                        "protected": b64_protected,  # always present by construction
                        "header": {"kid": did_key(verkey)},
                        "signature": b64_sig,
                    }
                )
            self.jws_ = AttachDecoratorDataJWS.deserialize(jws)

    async def verify(self, wallet: BaseWallet, signer_verkey: str = None) -> bool:
        """
        Verify the signature(s).

        Args:
            wallet: Wallet to use to verify signature

        Returns:
            True if verification succeeds else False

        """
        assert self.jws

        b64_payload = unpad(set_urlsafe_b64(self.base64, True))
        verkey_to_check = []
        for sig in [self.jws] if self.signatures == 1 else self.jws.signatures:
            b64_protected = sig.protected
            b64_sig = sig.signature
            protected = json.loads(b64_to_str(b64_protected, urlsafe=True))
            assert "jwk" in protected and protected["jwk"].get("kty") == "OKP"

            sign_input = (b64_protected + "." + b64_payload).encode("ascii")
            b_sig = b64_to_bytes(b64_sig, urlsafe=True)
            verkey = bytes_to_b58(b64_to_bytes(protected["jwk"]["x"], urlsafe=True))
            encoded_pk = DIDKey.from_did(protected["jwk"]["kid"]).public_key_b58
            verkey_to_check.append(encoded_pk)
            if not await wallet.verify_message(sign_input, b_sig, verkey, ED25519):
                return False
            if not await wallet.verify_message(sign_input, b_sig, encoded_pk, ED25519):
                return False
        if signer_verkey and signer_verkey not in verkey_to_check:
            return False
        return True

    def __eq__(self, other):
        """Compare equality with another."""

        for attr in ["jws_", "sha256_", "base64_"]:
            if getattr(self, attr, None) != getattr(other, attr, None):
                return False
        if set(getattr(self, "links_", [])) != set(getattr(other, "links_", [])):
            return False
        return True


class AttachDecoratorDataSchema(BaseModelSchema):
    """Attach decorator data schema."""

    class Meta:
        """Attach decorator data schema metadata."""

        model_class = AttachDecoratorData
        unknown = EXCLUDE

    @pre_load
    def validate_data_spec(self, data: Mapping, **kwargs):
        """Ensure model chooses exactly one of base64, json, or links."""

        if len(set(data.keys()) & {"base64", "json", "links"}) != 1:
            raise BaseModelError(
                "AttachDecoratorSchema: choose exactly one of base64, json, or links"
            )

        return data

    base64_ = fields.Str(
        required=False,
        data_key="base64",
        validate=BASE64_VALIDATE,
        metadata={"description": "Base64-encoded data", "example": BASE64_EXAMPLE},
    )
    jws_ = fields.Nested(
        AttachDecoratorDataJWSSchema,
        required=False,
        data_key="jws",
        metadata={"description": "Detached Java Web Signature"},
    )
    json_ = DictOrDictListField(
        required=False,
        data_key="json",
        metadata={
            "description": "JSON-serialized data",
            "example": '{"sample": "content"}',
        },
    )
    links_ = fields.List(
        fields.Str(metadata={"example": "https://link.to/data"}),
        required=False,
        data_key="links",
        metadata={"description": "List of hypertext links to data"},
    )
    sha256_ = fields.Str(
        required=False,
        data_key="sha256",
        validate=SHA256_VALIDATE,
        metadata={
            "description": "SHA256 hash (binhex encoded) of content",
            "example": SHA256_EXAMPLE,
        },
    )


class AttachDecorator(BaseModel):
    """Class representing attach decorator."""

    class Meta:
        """AttachDecorator metadata."""

        schema_class = "AttachDecoratorSchema"

    def __init__(
        self,
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        mime_type: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
        data: AttachDecoratorData,
        **kwargs,
    ):
        """
        Initialize an AttachDecorator instance.

        The attachment decorator allows for embedding or appending
        content to a message.

        Args:
            ident ("@id" in serialization): identifier for the appendage
            mime_type ("mime-type" in serialization): MIME type for attachment
            filename: file name
            lastmod_time: last modification time, "%Y-%m-%d %H:%M:%SZ"
            description: content description
            data: payload, as per `AttachDecoratorData`

        """
        super().__init__(**kwargs)
        self.ident = ident
        self.description = description
        self.filename = filename
        self.mime_type = mime_type
        self.lastmod_time = lastmod_time
        self.byte_count = byte_count
        self.data = data

    @property
    def content(self) -> Union[Mapping, Tuple[Sequence[str], str]]:
        """
        Return attachment content.

        Returns:
            data attachment, decoded if necessary and json-loaded, or data links
            and sha-256 hash.

        """
        if hasattr(self.data, "base64_"):
            return json.loads(b64_to_bytes(self.data.base64))
        elif hasattr(self.data, "json_"):
            return self.data.json
        elif hasattr(self.data, "links_"):
            return (  # fetching would be async; we want a property here
                self.data.links,
                self.data.sha256,
            )
        else:
            return None

    @classmethod
    def data_base64(
        cls,
        mapping: Mapping,
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
    ):
        """
        Create `AttachDecorator` instance on base64-encoded data from input mapping.

        Given mapping, JSON dump, base64-encode, and embed
        it as data; mark `application/json` MIME type.

        Args:
            mapping: (dict) data structure; e.g., indy production
            ident: optional attachment identifier (default random UUID4)
            description: optional attachment description
            filename: optional attachment filename
            lastmod_time: optional attachment last modification time
            byte_count: optional attachment byte count

        """
        return AttachDecorator(
            ident=ident or str(uuid.uuid4()),
            description=description,
            filename=filename,
            mime_type="application/json",
            lastmod_time=lastmod_time,
            byte_count=byte_count,
            data=AttachDecoratorData(
                base64_=bytes_to_b64(json.dumps(mapping).encode())
            ),
        )

    @classmethod
    def data_json(
        cls,
        mapping: Union[Sequence[dict], dict],
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
    ):
        """
        Create `AttachDecorator` instance on json-encoded data from input mapping.

        Given message object (dict), JSON dump, and embed
        it as data; mark `application/json` MIME type.

        Args:
            mapping: (dict) data structure; e.g., Aries message
            ident: optional attachment identifier (default random UUID4)
            description: optional attachment description
            filename: optional attachment filename
            lastmod_time: optional attachment last modification time
            byte_count: optional attachment byte count

        """
        return AttachDecorator(
            ident=ident or str(uuid.uuid4()),
            description=description,
            filename=filename,
            mime_type="application/json",
            lastmod_time=lastmod_time,
            byte_count=byte_count,
            data=AttachDecoratorData(json_=mapping),
        )

    @classmethod
    def data_links(
        cls,
        links: Union[str, Sequence[str]],
        sha256: str = None,
        *,
        ident: str = None,
        mime_type: str = None,
        description: str = None,
        filename: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
    ):
        """
        Create `AttachDecorator` instance on json-encoded data from input mapping.

        Given message object (dict), JSON dump, and embed
        it as data; mark `application/json` MIME type.

        Args:
            links: URL or list of URLs
            sha256: optional sha-256 hash for content
            ident: optional attachment identifier (default random UUID4)
            mime_type: optional MIME type
            description: optional attachment description
            filename: optional attachment filename
            lastmod_time: optional attachment last modification time
            byte_count: optional attachment byte count

        """
        return AttachDecorator(
            ident=ident or str(uuid.uuid4()),
            description=description,
            filename=filename,
            mime_type=mime_type or "application/json",
            lastmod_time=lastmod_time,
            byte_count=byte_count,
            data=AttachDecoratorData(sha256_=sha256, links_=links),
        )


class AttachDecoratorSchema(BaseModelSchema):
    """Attach decorator schema used in serialization/deserialization."""

    class Meta:
        """AttachDecoratorSchema metadata."""

        model_class = AttachDecorator
        unknown = EXCLUDE

    ident = fields.Str(
        required=False,
        allow_none=False,
        data_key="@id",
        metadata={"description": "Attachment identifier", "example": UUID4_EXAMPLE},
    )
    mime_type = fields.Str(
        required=False,
        data_key="mime-type",
        metadata={"description": "MIME type", "example": "image/png"},
    )
    filename = fields.Str(
        required=False,
        metadata={"description": "File name", "example": "IMG1092348.png"},
    )
    byte_count = fields.Int(
        required=False,
        metadata={
            "description": "Byte count of data included by reference",
            "example": 1234,
            "strict": True,
        },
    )
    lastmod_time = fields.Str(
        required=False,
        validate=INDY_ISO8601_DATETIME_VALIDATE,
        metadata={
            "description": (
                "Hint regarding last modification datetime, in ISO-8601 format"
            ),
            "example": INDY_ISO8601_DATETIME_EXAMPLE,
        },
    )
    description = fields.Str(
        required=False,
        metadata={
            "description": "Human-readable description of content",
            "example": "view from doorway, facing east, with lights off",
        },
    )
    data = fields.Nested(AttachDecoratorDataSchema, required=True)
