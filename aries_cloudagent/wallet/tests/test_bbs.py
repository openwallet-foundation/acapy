from unittest import TestCase
import pytest

from ..bbs import (
    sign_messages_bls12381g2,
    verify_signed_messages_bls12381g2,
    create_bls12381g2_keypair,
    BbsException,
)

PUBLIC_KEY_BYTES = b"\x8c\xa2\xbe \xad\x9c\xf9\x98\x04e\x17\xec\x00\xf9J\xd7\xed\xdb\xa4\x0el\x9fG\x94\x9b+d\xac\xf5\x0f{\xf3\xa1\xc7\xd9\xa7*YZ\xa78\x86\x8b\xcc\xb8\x9d\x86\xcb\x07\x8b\xfak9\xd8\xb8\\\x93\x86\xc8\xf7\xb1O\x88\x17\xa4\xc9x5\xdd\x04e\xee'\xff\x05\xf8&EU\xfa\x8f\x83\xa3#\xca\x9b\xdf\xa8\xc2\xda\x0fz\x8f\x05@o"
SECRET_KEY_BYTES = b"TmL\x10\xd4k[\x8b\xc3\xb7\x91\xd5\x90\xaf4\xbe\xdc\x89f\xb4\r\xbeV\xbdq>\xbd=\xee\x97\x86\x01"
SIGNED_BYTES = b"\x82\xd7\x9c\xa9\x05\xe1\xb8\x0c\x92\xa1Jr\xd0G%\x18`P\x0e\xa8\xf6\xcapWe\xa0\xc0\xa1c\x92Tr\xb6k\xf1\xa5\x196\xbd\xa4\x94\xe0\xeatO$Re>\x10\x05[?\x93\x8f\x03\x8d\xa1\x11r\x98\xd5\x17\xf4\xe4\xb5\x80\xcbh\xfc_\x8cy\xe8p\x98\x1d\xcd\xeb+*\xf7E\xa1\x10\xf3\xa5\x8f^\xda\xba\xc5&\xb9\xdfI\xe6bl\xdcx\x7fM\xc6\xbf,eA|\x99h\xcd"
SIGN_MESSAGES = [b"messag1", b"message2"]
SEED = "seed000000000001"


@pytest.mark.ursa_bbs_signatures
class TestBBS(TestCase):
    def test_create_keypair_seed(self):
        (pk, sk) = create_bls12381g2_keypair(SEED)

        assert pk == PUBLIC_KEY_BYTES
        assert sk == SECRET_KEY_BYTES

    def test_create_keypair(self):
        (pk, sk) = create_bls12381g2_keypair()

        assert pk
        assert sk

    def test_create_keypair_x_invalid_seed(self):
        with self.assertRaises(BbsException) as context:
            create_bls12381g2_keypair(10)
        assert "Unable to create keypair" in str(context.exception)

    def test_sign(self):
        signed = sign_messages_bls12381g2(SIGN_MESSAGES, SECRET_KEY_BYTES)

        assert signed

        assert verify_signed_messages_bls12381g2(
            SIGN_MESSAGES, signed, PUBLIC_KEY_BYTES
        )

    def test_sign_x_invalid_secret_key_bytes(self):
        with self.assertRaises(BbsException) as context:
            sign_messages_bls12381g2(SIGN_MESSAGES, "hello")
        assert "Unable to sign messages" in str(context.exception)

    def test_verify(self):
        assert verify_signed_messages_bls12381g2(
            SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES
        )

    def test_verify_x_invalid_pk(self):
        with self.assertRaises(BbsException):
            verify_signed_messages_bls12381g2(
                SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES + b"10"
            )

    def test_verify_x_invalid_messages(self):
        with self.assertRaises(BbsException):
            verify_signed_messages_bls12381g2(
                SIGN_MESSAGES, SIGNED_BYTES, PUBLIC_KEY_BYTES + b"10"
            )
        assert not verify_signed_messages_bls12381g2(
            [SIGN_MESSAGES[0]], SIGNED_BYTES, PUBLIC_KEY_BYTES
        )

    def test_verify_x_invalid_signed_bytes(self):
        with self.assertRaises(BbsException):
            assert not verify_signed_messages_bls12381g2(
                SIGN_MESSAGES, SIGNED_BYTES + b"10", PUBLIC_KEY_BYTES
            )
