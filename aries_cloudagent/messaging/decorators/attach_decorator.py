"""
A message decorator for attachments.

An attach decorator embeds content or specifies appended content.
"""


import json
import re
import uuid

from typing import Mapping, Union

from marshmallow import fields

from ...wallet.base import BaseWallet
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
from ..models.base import BaseModel, BaseModelSchema
from ..valid import (
    BASE64,
    INDY_ISO8601_DATETIME,
    SHA256,
    UUIDFour,
)


class AttachDecoratorData(BaseModel):
    """Attach decorator data."""

    class Meta:
        """AttachDecoratorData metadata."""

        schema_class = "AttachDecoratorDataSchema"

    def __init__(
        self,
        *,
        base64_: str = None,
        sig_: str = None,
        json_: str = None,
        links_: Union[list, str] = None,
        sha256_: str = None,
    ):
        """
        Initialize decorator data.

        Specify content for one of:

            - `base64_`
            - `sig_`
            - `json_`
            - `links_` and optionally `sha256_`.

        Args:
            base64_: base64 encoded content for inclusion
            sig_: signed content for inclusion
            json_: json-dumped content for inclusion
            links_: list or single URL of hyperlinks
            sha256_: sha-256 hash for URL content, if `links_` specified

        """
        if base64_:
            self.base64_ = base64_
        elif sig_:
            self.sig_ = sig_
        elif json_:
            self.json_ = json_
        else:
            assert isinstance(links_, (str, list))
            self.links_ = [links_] if isinstance(links_, str) else list(links_)
            if sha256_:
                self.sha256_ = sha256_

    @property
    def base64(self):
        """Accessor for base64 decorator data, or None."""
        return getattr(self, "base64_", None)

    @property
    def sig(self):
        """Accessor for signed-content decorator data, or None."""
        return getattr(self, "sig_", None)

    @property
    def signatures(self) -> int:
        """Accessor for number of signatures."""
        if self.sig:
            if isinstance(self.sig, str):
                assert re.match(
                    r"^[-_a-zA-Z0-9]*\.[-_a-zA-Z0-9]*\.[-_a-zA-Z0-9]*$",
                    self.sig
                )
                return 1
            return len(self.sig["signatures"])
        return 0

    @property
    def signed(self) -> bytes:
        """Accessor for signed content (payload), None for unsigned."""
        if self.sig:
            if self.signatures == 1:
                return b64_to_bytes(self.sig.split(".")[1], urlsafe=True)
            return b64_to_bytes(self.sig["payload"], urlsafe=True)
        return None

    def header(self, idx: int = 0, jose: bool = True) -> Mapping:
        """
        Accessor for header info at input index, default 0 or unique for singly-signed.

        Args:
            idx: index of interest, zero-based (default 0)
            jose: True to return unprotected header attributes, False for protected only

        """
        if self.signatures == 1:
            return json.loads(b64_to_str(self.sig.split(".")[0], urlsafe=True))
        if self.signatures > 1:
            headers = json.loads(b64_to_str(
                self.sig["signatures"][idx]["protected"],
                urlsafe=True,
            ))
            if jose:
                headers.update(self.sig["signatures"][idx]["header"])
            return headers
        return None

    @property
    def json(self):
        """Accessor for json decorator data, or None."""
        return getattr(self, "json_", None)

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
        verkeys: Union[str, Mapping[str, str]],
        wallet: BaseWallet,
    ):
        """
        Sign and replace base64 data value of attachment.

        Args:
            verkeys: Verkey(s) of the signing party; specify:
                - single verkey alone for single signature with no key identifier (kid)
                - dict mapping single key identifier to verkey for single signature
                - dict mapping key identifiers to verkeys for multi-signature
            wallet: The wallet to use for the signature

        """
        def build_protected(verkey: str, kid: str, protect_kid: bool):
            """Build protected header."""
            return str_to_b64(
                json.dumps({
                    "alg": "EdDSA",
                    **{"kid": k for k in [kid] if kid and protect_kid},
                    "jwk": {
                        "kty": "OKP",
                        "crv": "Ed25519",
                        "x": bytes_to_b64(
                            b58_to_bytes(verkey),
                            urlsafe=True,
                            pad=False
                        ),
                        **{"kid": k for k in [kid] if kid},
                    },
                }),
                urlsafe=True,
                pad=False
            )

        assert self.base64_

        b64_payload = unpad(set_urlsafe_b64(self.base64_, True))

        if (
            isinstance(verkeys, str) or
            (isinstance(verkeys, Mapping) and len(verkeys) == 1)
        ):
            kid = list(verkeys)[0] if isinstance(verkeys, Mapping) else None
            verkey = verkeys[kid] if isinstance(verkeys, Mapping) else verkeys
            b64_protected = build_protected(verkey, kid, protect_kid=True)
            b64_sig = bytes_to_b64(
                await wallet.sign_message(
                    message=(b64_protected + "." + b64_payload).encode("ascii"),
                    from_verkey=verkey
                ),
                urlsafe=True,
                pad=False,
            )
            self.sig_ = ".".join([b64_protected, b64_payload, b64_sig])
        else:
            sig = {"payload": b64_payload, "signatures": []}
            for (kid, verkey) in verkeys.items():
                assert kid is not None
                b64_protected = build_protected(verkey, kid, protect_kid=False)
                b64_sig = bytes_to_b64(
                    await wallet.sign_message(
                        message=(b64_protected + "." + b64_payload).encode("ascii"),
                        from_verkey=verkey
                    ),
                    urlsafe=True,
                    pad=False,
                )
                sig["signatures"].append(
                    {
                        "protected": b64_protected,
                        "header": {"kid": kid},
                        "signature": b64_sig
                    }
                )
            self.sig_ = sig

        self.base64_ = None

    async def verify(self, wallet: BaseWallet) -> bool:
        """
        Verify the signature(s).

        Args:
            wallet: Wallet to use to verify signature

        Returns:
            True if verification succeeds else False

        """
        assert self.sig

        if self.signatures == 1:
            (b64_protected, b64_payload, b64_sig) = self.sig.split(".")
            protected = json.loads(b64_to_str(b64_protected, urlsafe=True))
            assert "jwk" in protected and protected["jwk"].get("kty") == "OKP"

            sign_input = (b64_protected + "." + b64_payload).encode("ascii")
            b_sig = b64_to_bytes(b64_sig, urlsafe=True)
            verkey = bytes_to_b58(b64_to_bytes(protected["jwk"]["x"], urlsafe=True))

            return await wallet.verify_message(sign_input, b_sig, verkey)
        else:
            b64_payload = self.sig["payload"]
            for signature in self.sig["signatures"]:
                b64_protected = signature["protected"]
                b64_sig = signature["signature"]
                protected = json.loads(b64_to_str(b64_protected, urlsafe=True))
                assert "jwk" in protected and protected["jwk"].get("kty") == "OKP"

                sign_input = (b64_protected + "." + b64_payload).encode("ascii")
                b_sig = b64_to_bytes(b64_sig, urlsafe=True)
                verkey = bytes_to_b58(b64_to_bytes(protected["jwk"]["x"], urlsafe=True))
                if not await wallet.verify_message(sign_input, b_sig, verkey):
                    return False
            return True

    def __eq__(self, other):
        """Equality comparator."""
        for attr in ["base64_", "sig_", "json_", "sha256_"]:
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

    base64_ = fields.Str(
        description="Base64-encoded data",
        required=False,
        data_key="base64",
        **BASE64
    )
    sig_ = fields.Str(
        description="Signed content, replacing base64-encoded data",
        required=False,
        data_key="sig",
        example=(
            "eyJhbGciOiJFZERTQSJ9."
            "eyJhIjogIjAifQ."
            "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        ),
    )
    json_ = fields.Str(
        description="JSON-serialized data",
        required=False,
        example='{"sample": "content"}',
        data_key="json"
    )
    links_ = fields.List(
        fields.Str(example="https://link.to/data"),
        description="List of hypertext links to data",
        required=False,
        data_key="links"
    )
    sha256_ = fields.Str(
        description="SHA256 hash of linked data",
        required=False,
        data_key="sha256",
        **SHA256
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
        **kwargs
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
    def indy_dict(self):
        """
        Return indy data structure encoded in attachment.

        Returns: dict with indy object in data attachment

        """
        assert hasattr(self.data, "base64_")
        return json.loads(b64_to_bytes(self.data.base64_))

    @classmethod
    def from_indy_dict(
        cls,
        indy_dict: dict,
        *,
        ident: str = None,
        description: str = None,
        filename: str = None,
        lastmod_time: str = None,
        byte_count: int = None,
    ):
        """
        Create `AttachDecorator` instance from indy object (dict).

        Given indy object (dict), JSON dump, base64-encode, and embed
        it as data; mark `application/json` MIME type.

        Args:
            indy_dict: indy (dict) data structure
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
                base64_=bytes_to_b64(json.dumps(indy_dict).encode())
            )
        )


class AttachDecoratorSchema(BaseModelSchema):
    """Attach decorator schema used in serialization/deserialization."""

    class Meta:
        """AttachDecoratorSchema metadata."""

        model_class = AttachDecorator

    ident = fields.Str(
        description="Attachment identifier",
        example=UUIDFour.EXAMPLE,
        required=False,
        allow_none=False,
        data_key="@id"
    )
    mime_type = fields.Str(
        description="MIME type",
        example="image/png",
        required=False,
        data_key="mime-type"
    )
    filename = fields.Str(
        description="File name",
        example="IMG1092348.png",
        required=False
    )
    byte_count = fields.Integer(
        description="Byte count of data included by reference",
        example=1234,
        required=False
    )
    lastmod_time = fields.Str(
        description="Hint regarding last modification datetime, in ISO-8601 format",
        required=False,
        **INDY_ISO8601_DATETIME
    )
    description = fields.Str(
        description="Human-readable description of content",
        example="view from doorway, facing east, with lights off",
        required=False
    )
    data = fields.Nested(
        AttachDecoratorDataSchema,
        required=True,
    )
