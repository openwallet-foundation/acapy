"""BBS+ crypto."""

from typing import List, Tuple
from ursa_bbs_signatures import (
    SignRequest,
    VerifyRequest,
    BlsKeyPair,
    sign as bbs_sign,
    verify as bbs_verify,
)

from ..wallet.util import random_seed


def sign_messages_bls12381g2(messages: List[bytes], secret: bytes):
    """Sign messages using a bls12381g2 private signing key.

    Args:
        messages (List[bytes]): The messages to sign
        secret (bytes): The private signing key

    Returns:
        bytes: The signature

    """
    key_pair = BlsKeyPair.from_secret_key(secret)

    messages = [message.decode("utf-8") for message in messages]

    sign_request = SignRequest(key_pair=key_pair, messages=messages)

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
    key_pair = BlsKeyPair(public_key=public_key)
    messages = [message.decode("utf-8") for message in messages]

    verify_request = VerifyRequest(
        key_pair=key_pair, signature=signature, messages=messages
    )

    return bbs_verify(verify_request)


def create_bls12381g2_keypair(seed: bytes = None) -> Tuple[bytes, bytes]:
    """
    Create a public and private bls12381g2 keypair from a seed value.

    Args:
        seed: Seed for keypair

    Returns:
        A tuple of (public key, secret key)

    """
    if not seed:
        seed = random_seed()

    key_pair = BlsKeyPair.generate_g2(seed)
    return key_pair.public_key, key_pair.secret_key
