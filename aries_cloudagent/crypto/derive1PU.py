from ecdsa import ECDH, NIST256p, SigningKey
from deriveECDH import *

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
from cryptography.hazmat.backends import default_backend

# ECDH-1PU generates a shared encryption key from two intermediate keys concatenated together
# The two keys are generated from ECDH-ES, one pair from sender/receiver (zs), the second pair from ephemeral sender/receiver (ze)
def derive1PU(ze, zs):

    prefix = bytearray(b"0001")

    z = prefix + ze + zs
    otherinfo = b"alg_id + apu_info + apv_info + pub_info"

    key = ConcatKDF(z, otherinfo)
    
    return key

# The sender generates two intermediate keys (ze, zs) from two shared secrets (se, ss)
def deriveSender1PU(senderEphemeralPriv, senderPriv, recvPub):
    
    se = DeriveECDHSecret(senderEphemeralPriv, recvPub)
    ze = ConcatKDF(se)

    ss = DeriveECDHSecret(senderPriv, recvPub)
    zs = ConcatKDF(ss)

    key = derive1PU(ze, zs)

    return key

# The receiver generates two intermediate keys (ze, zs) from two shared secrets (se, ss)
def deriveReceiver1PU(senderEphemeralPub, senderPub, recvPriv):
    se = DeriveECDHSecret(recvPriv, senderEphemeralPub)
    ze = ConcatKDF(se)

    ss = DeriveECDHSecret(recvPriv, senderPub)
    zs = ConcatKDF(ss)

    key = derive1PU(ze, zs)

    return key

