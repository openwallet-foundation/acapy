"""Model and schema for working with field signatures within message bodies."""

import json
import struct
import time

from marshmallow import EXCLUDE, fields

from ...protocols.didcomm_prefix import DIDCommPrefix
from ...wallet.base import BaseWallet
from ...wallet.key_type import ED25519
from ...wallet.util import b64_to_bytes, bytes_to_b64
from ..models.base import BaseModel, BaseModelSchema
from ..valid import (
    BASE64URL_EXAMPLE,
    BASE64URL_VALIDATE,
    INDY_RAW_PUBLIC_KEY_EXAMPLE,
    INDY_RAW_PUBLIC_KEY_VALIDATE,
)


class SignatureDecorator(BaseModel):
    """Class representing a field value signed by a known verkey."""

    class Meta:
        """SignatureDecorator metadata."""

        schema_class = "SignatureDecoratorSchema"

    TYPE_ED25519SHA512 = "signature/1.0/ed25519Sha512_single"

    def __init__(
        self,
        *,
        signature_type: str = None,
        signature: str = None,
        sig_data: str = None,
        signer: str = None,
    ):
        """
        Initialize a FieldSignature instance.

        Args:
            signature_type: Type of signature
            signature: The signature
            sig_data: Signature data
            signer: The verkey of the signer
        """
        self.signature_type = signature_type
        self.signature = signature
        self.sig_data = sig_data
        self.signer = signer

    @classmethod
    async def create(
        cls, value, signer: str, wallet: BaseWallet, timestamp=None
    ) -> "SignatureDecorator":
        """
        Create a Signature.

        Sign a field value and return a newly constructed `SignatureDecorator`
        representing the resulting signature.

        Args:
            value: Value to sign
            signer: Verkey of the signing party
            wallet: The wallet to use for the signature

        Returns:
            The created `SignatureDecorator` object

        """
        if not timestamp:
            timestamp = time.time()
        if isinstance(value, BaseModel):
            value = value.serialize()
        # 8 byte, big-endian encoded, unsigned int (long)
        timestamp_bin = struct.pack("!Q", int(timestamp))
        msg_combined_bin = timestamp_bin + json.dumps(value).encode("ascii")
        signature_bin = await wallet.sign_message(msg_combined_bin, signer)
        return SignatureDecorator(
            signature_type=DIDCommPrefix.qualify_current(cls.TYPE_ED25519SHA512),
            signature=bytes_to_b64(signature_bin, urlsafe=True),
            sig_data=bytes_to_b64(msg_combined_bin, urlsafe=True),
            signer=signer,
        )

    def decode(self) -> (object, int):
        """
        Decode the signature to its timestamp and value.

        Returns:
            A tuple of (decoded message, timestamp)

        """
        msg_bin = b64_to_bytes(self.sig_data, urlsafe=True)
        (timestamp,) = struct.unpack_from("!Q", msg_bin, 0)
        return (json.loads(msg_bin[8:]), timestamp)

    async def verify(self, wallet: BaseWallet) -> bool:
        """
        Verify the signature against the signer's public key.

        Args:
            wallet: Wallet to use to verify signature

        Returns:
            True if verification succeeds else False

        """
        if self.signature_type not in [
            prefix.qualify(SignatureDecorator.TYPE_ED25519SHA512)
            for prefix in DIDCommPrefix
        ]:
            return False
        msg_bin = b64_to_bytes(self.sig_data, urlsafe=True)
        sig_bin = b64_to_bytes(self.signature, urlsafe=True)
        return await wallet.verify_message(msg_bin, sig_bin, self.signer, ED25519)

    def __str__(self):
        """Get a string representation of this class."""
        return (
            f"{self.__class__.__name__}"
            + f"(signature_type='{self.signature_type,}', "
            + f"signature='{self.signature,}', "
            + f"sig_data='{self.sig_data}', signer='{self.signer}')"
        )


class SignatureDecoratorSchema(BaseModelSchema):
    """SignatureDecorator schema."""

    class Meta:
        """SignatureDecoratorSchema metadata."""

        model_class = SignatureDecorator
        unknown = EXCLUDE

    signature_type = fields.Str(
        data_key="@type",
        required=True,
        metadata={
            "description": "Signature type",
            "example": DIDCommPrefix.NEW.qualify("signature/1.0/ed25519Sha512_single"),
        },
    )
    signature = fields.Str(
        required=True,
        validate=BASE64URL_VALIDATE,
        metadata={
            "description": "signature value, base64url-encoded",
            "example": (
                "FpSxSohK3rhn9QhcJStUNRYUvD8OxLuwda3yhzHkWbZ0VxIbI-l4mKOz7AmkMHDj2"
                "IgDEa1-GCFfWXNl96a7Bg=="
            ),
        },
    )
    sig_data = fields.Str(
        required=True,
        validate=BASE64URL_VALIDATE,
        metadata={
            "description": "Signature data, base64url-encoded",
            "example": BASE64URL_EXAMPLE,
        },
    )
    signer = fields.Str(
        required=True,
        validate=INDY_RAW_PUBLIC_KEY_VALIDATE,
        metadata={
            "description": "Signer verification key",
            "example": INDY_RAW_PUBLIC_KEY_EXAMPLE,
        },
    )
