"""
A message decorator for attachments.

An attach decorator embeds content or specifies appended content.
"""


import json
import struct
import uuid

from time import time
from typing import Union

from marshmallow import fields

from ...wallet.base import BaseWallet
from ...wallet.util import b64_to_bytes, bytes_to_b64, set_urlsafe_b64
from ..models.base import BaseModel, BaseModelSchema
from ..valid import (
    BASE64,
    Base64URL,
    INDY_ISO8601_DATETIME,
    INDY_RAW_PUBLIC_KEY,
    INT_EPOCH,
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
        base64_: str = None,
        json_: str = None,
        links_: Union[list, str] = None,
        sha256_: str = None
    ):
        """
        Initialize decorator data.

        Specify content for one of:

            - `base64_`
            - `json_`
            - `links_` and optionally `sha256_`.

        Args:
            base64_: base64 encoded content for inclusion.
            json_: json-dumped content for inclusion.
            links_: list or single URL of hyperlinks.
            sha256_: sha-256 hash for URL content, if `links_` specified.

        """
        if base64_:
            self.base64_ = base64_
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

    def __eq__(self, other):
        """Equality comparator."""
        for attr in ["base64_", "json_", "sha256_"]:
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
        attribute="base64_",
        data_key="base64",
        **BASE64
    )
    json_ = fields.Str(
        description="JSON-serialized data",
        required=False,
        example='{"sample": "content"}',
        attribute="json_",
        data_key="json"
    )
    links_ = fields.List(
        fields.Str(example="https://link.to/data"),
        description="List of hypertext links to data",
        required=False,
        attribute="links_",
        data_key="links"
    )
    sha256_ = fields.Str(
        description="SHA256 hash of linked data",
        required=False,
        attribute="sha256_",
        data_key="sha256",
        **SHA256
    )


class AttachDecoratorSig(BaseModel):
    """Attach decorator signature."""

    class Meta:
        """Attach decorator signature metadata."""

        schema_class = "AttachDecoratorSigSchema"

    TYPE_ED25519SHA512 = (
        "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/signature/1.0/ed25519Sha512_single"
    )

    def __init__(
        self,
        *,
        signature_type: str = None,
        ts: int = None,
        signature: str = None,
        signers: str = None,
    ):
        """
        Initialize a FieldSignature instance.

        Args:
            signature_type: Type of signature
            ts: Timestamp (epoch seconds), default now
            signature: The signature
            signers: The verkey of the signer

        """
        self.signature_type = signature_type or AttachDecoratorSig.TYPE_ED25519SHA512
        self.ts = ts or int(time())
        self.signature = signature
        self.signers = signers

    def decode(self) -> (object, int):
        """
        Decode the signature to its timestamp and value.

        Returns:
            A tuple of (decoded message, timestamp)

        """
        b_msg = b64_to_bytes(self.signature, urlsafe=True)
        (timestamp,) = struct.unpack_from("!Q", b_msg, 0)
        return (json.loads(b_msg[8:]), timestamp)


class AttachDecoratorSigSchema(BaseModelSchema):
    """Attach decorator signature schema."""

    class Meta:
        """Attach decorator data signature schema metadata."""

        model_class = AttachDecoratorSig

    signature_type = fields.Constant(
        constant=AttachDecoratorSig.TYPE_ED25519SHA512,
        description=f"Signature type: {AttachDecoratorSig.TYPE_ED25519SHA512}",
        required=False,
        data_key="type",
        example=AttachDecoratorSig.TYPE_ED25519SHA512,
    )
    ts = fields.Int(
        description="Timestamp as EPOCH int",
        required=False,
        **INT_EPOCH
    )
    signature = fields.Str(
        required=True,
        description="Signature value, base64url-encoded",
        example=(
            "FpSxSohK3rhn9QhcJStUNRYUvD8OxLuwda3yhzHkWbZ0VxIbI-"
            "l4mKOz7AmkMHDj2IgDEa1-GCFfWXNl96a7Bg=="
        ),
        validate=Base64URL(),
    )
    signers = fields.Str(
        required=True,
        description="Signer verification key (singular for the present)",
        **INDY_RAW_PUBLIC_KEY
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
        sig: AttachDecoratorSig = None,
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
            sig: signature, as per `AttachDecoratorSig`

        """
        super().__init__(**kwargs)
        self.ident = ident
        self.description = description
        self.filename = filename
        self.mime_type = mime_type
        self.lastmod_time = lastmod_time
        self.byte_count = byte_count
        self.data = data
        self.sig = sig

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

    def _pack_bytes(self, timestamp: int) -> bytes:
        """
        Timestamp and struct-pack data for signing.

        Args:
            timestamp: timestamp (EPOCH seconds)

        Returns:
            Packed bytes on timestamp and base64url-encoded data to sign

        """
        assert self.data and self.data.base64

        b_timestamp = struct.pack("!Q", int(timestamp))

        b_value = set_urlsafe_b64(self.data.base64, urlsafe=True).encode("ascii")
        # 8 byte, big-endian encoded, unsigned int (long)
        b_timestamp = struct.pack("!Q", int(timestamp))

        return b_timestamp + b_value

    async def sign(self, signer: str, wallet: BaseWallet, timestamp: int = None):
        """
        Sign data value of attachment and set the resulting signature content.

        Args:
            signer: Verkey of the signing party
            wallet: The wallet to use for the signature
            timestamp: Epoch (integer) time of signature, default now

        """
        if not timestamp:
            timestamp = int(time())

        b_msg = self._pack_bytes(timestamp)
        b64_sig = bytes_to_b64(
            await wallet.sign_message(message=b_msg, from_verkey=signer),
            urlsafe=True,
        )
        self.sig = AttachDecoratorSig(
            signature_type=None,
            ts=timestamp,
            signature=b64_sig,
            signers=signer,
        )

    async def verify(self, wallet: BaseWallet) -> bool:
        """
        Verify the signature against the signer's public key.

        Args:
            wallet: Wallet to use to verify signature

        Returns:
            True if verification succeeds else False

        """
        if self.sig.signature_type != AttachDecoratorSig.TYPE_ED25519SHA512:
            return False
        b_msg = self._pack_bytes(self.sig.ts)
        b_sig = b64_to_bytes(self.sig.signature, urlsafe=True)
        return await wallet.verify_message(b_msg, b_sig, self.sig.signers)


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
    sig = fields.Nested(
        AttachDecoratorSigSchema,
        required=False,
    )
