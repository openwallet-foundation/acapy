"""
Model and schema for working with field signatures within message bodies
"""

from abc import ABC
import json
import struct
import sys
import time

from marshmallow import (
    Schema, fields, post_dump, pre_load, post_load,
)

from .base import BaseModel, BaseModelSchema
from ..wallet import BaseWallet
from ..wallet.util import b64_to_bytes, bytes_to_b64


class FieldSignature(BaseModel):
    """
    Class representing a field value signed by a known verkey
    """
    class Meta:
        schema_class = 'FieldSignatureSchema'

    TYPE_ED25519SHA512 = "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/signature/1.0/ed25519Sha512_single"

    def __init__(
            self,
            *,
            type: str = None,
            signature: str = None,
            sig_data: str = None,
            signer: str = None,
        ):
        self.signature_type = type
        self.signature = signature
        self.sig_data = sig_data
        self.signer = signer

    @classmethod
    async def create(
            cls, value, signer: str, wallet: BaseWallet, timestamp = None
        ) -> 'FieldSignature':
        """
        Sign a field value and return a newly constructed `FieldSignature` representing
        the resulting signature
        """
        if not timestamp:
            timestamp = time.time()
        # 8 byte, big-endian encoded, unsigned int (long)
        timestamp_bin = struct.pack("!Q", int(timestamp))
        msg_combined_bin = timestamp_bin + json.dumps(value).encode("ascii")
        signature_bin = await wallet.sign_message(msg_combined_bin, signer)
        return FieldSignature(
            type=cls.TYPE_ED25519SHA512,
            signature=bytes_to_b64(signature_bin, urlsafe=True),
            sig_data=bytes_to_b64(msg_combined_bin, urlsafe=True),
            signer=signer,
        )

    def decode(self) -> (object, int):
        """
        Decode the signature to its timestamp and value
        """
        msg_bin = b64_to_bytes(self.sig_data, urlsafe=True)
        timestamp, = struct.unpack_from("!Q", msg_bin, 0)
        return json.loads(msg_bin[8:]), timestamp

    async def verify(self, wallet: BaseWallet) -> bool:
        """
        Verify the signature against the signer's public key
        """
        msg_bin = b64_to_bytes(self.sig_data, urlsafe=True)
        sig_bin = b64_to_bytes(self.signature, urlsafe=True)
        return await wallet.verify_message(msg_bin, sig_bin, self.signer)

    def __str__(self):
        return "{}(signature_type='{}', signature='{}', sig_data='{}', signer='{}')".format(
            self.__class__.__name__,
            self.signature_type, self.signature, self.sig_data, self.signer,
        )


class FieldSignatureSchema(BaseModelSchema):
    class Meta:
        model_class = FieldSignature
    sig_type = fields.Str(data_key="@type")
    signature = fields.Str()
    sig_data = fields.Str()
    signer = fields.Str()
