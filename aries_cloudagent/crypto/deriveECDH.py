"""Functions for performing Key Agreement."""

from ecdsa import ECDH, NIST256p
from binascii import unhexlify
import hashlib


def DeriveECDHSecret(privateKey, publicKey):
    """Generate a shared secret from keys in byte format."""

    derive = ECDH(curve=NIST256p)
    derive.load_private_key_bytes(unhexlify(privateKey))
    derive.load_received_public_key_bytes(unhexlify(publicKey))

    secret = derive.generate_sharedsecret_bytes()
    return secret


def DeriveECDHSecretFromKey(privateKey, publicKey):
    """Generate a shared secret from keys in ecdsa.Keys format."""

    derive = ECDH(curve=NIST256p)
    derive.load_private_key(privateKey)
    derive.load_received_public_key(publicKey)

    secret = derive.generate_sharedsecret_bytes()
    return secret


def ConcatKDF(sharedSecret, alg, apu, apv, keydatalen):
    """Generate a shared encryption key from a shared secret."""

    # ECDH-1PU requires a "round number 1" to be prefixed onto the shared secret z
    prefix = (1).to_bytes(4, "big")
    sharedSecret = prefix + sharedSecret

    # ECDH-1PU requires each of the header parameters
    # to be front padded with their length
    alg = bytes(alg, "utf-8")
    apu = bytes(apu, "utf-8")
    apv = bytes(apv, "utf-8")

    AlgID = len(alg).to_bytes(4, "big") + alg
    PartyUInfo = len(apu).to_bytes(4, "big") + apu
    PartyVInfo = len(apv).to_bytes(4, "big") + apv
    SuppPubInfo = (keydatalen * 8).to_bytes(4, "big")

    otherinfo = AlgID + PartyUInfo + PartyVInfo + SuppPubInfo

    # The concatKDF input is: Round1 + ze + zs + otherinfo
    sharedSecret = sharedSecret + otherinfo
    # Use sha256 for concatKDF
    sharedKey = hashlib.sha256(sharedSecret).digest()

    return sharedKey
