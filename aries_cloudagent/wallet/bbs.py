"""BBS+ crypto."""

from typing import List, Tuple

from ..utils.dependencies import (
    assert_ursa_bbs_signatures_installed,
    is_ursa_bbs_signatures_module_installed,
)
from ..core.error import BaseError
from ..wallet.util import random_seed

if is_ursa_bbs_signatures_module_installed():
    from ursa_bbs_signatures import (
        SignRequest,
        VerifyRequest,
        BlsKeyPair,
        sign as bbs_sign,
        verify as bbs_verify,
        BbsException as NativeBbsException,
    )
    from ursa_bbs_signatures._ffi.FfiException import FfiException


class BbsException(BaseError):
    """Base BBS exception."""


def sign_messages_bls12381g2(messages: List[bytes], secret: bytes):
    """Sign messages using a bls12381g2 private signing key.

    Args:
        messages (List[bytes]): The messages to sign
        secret (bytes): The private signing key

    Returns:
        bytes: The signature

    """
    assert_ursa_bbs_signatures_installed()

    messages = [message.decode("utf-8") for message in messages]
    try:
        key_pair = BlsKeyPair.from_secret_key(secret)
        sign_request = SignRequest(key_pair=key_pair, messages=messages)
    except (
        FfiException,
        NativeBbsException,
    ) as error:  # would be nice to be able to distinct between false and error
        raise BbsException("Unable to sign messages") from error

    return bbs_sign(sign_request)


def verify_signed_messages_bls12381g2(
    messages: List[bytes], signature: bytes, public_key: bytes
) -> bool:
    """
    Verify an ed25519 signed message according to a public verification key.

    Args:
        signed: The signed messages
        public_key: The public key to use in verification

    Returns:
        True if verified, else False

    """
    assert_ursa_bbs_signatures_installed()

    key_pair = BlsKeyPair(public_key=public_key)
    messages = [message.decode("utf-8") for message in messages]

    verify_request = VerifyRequest(
        key_pair=key_pair, signature=signature, messages=messages
    )

    try:
        return bbs_verify(verify_request)
    except (
        FfiException,
        NativeBbsException,
    ) as error:  # would be nice to be able to distinct between false and error
        raise BbsException("Unable to verify BBS+ signature") from error


def create_bls12381g2_keypair(seed: bytes = None) -> Tuple[bytes, bytes]:
    """
    Create a public and private bls12381g2 keypair from a seed value.

    Args:
        seed: Seed for keypair

    Returns:
        A tuple of (public key, secret key)

    """
    assert_ursa_bbs_signatures_installed()

    if not seed:
        seed = random_seed()

    try:
        key_pair = BlsKeyPair.generate_g2(seed)
        return key_pair.public_key, key_pair.secret_key
    except Exception as error:
        raise BbsException("Unable to create keypair") from error
