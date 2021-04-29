from ecdsa import ECDH, NIST256p
from deriveECDH import *

# ECDH-1PU generates a shared encryption key from two concatenated ECDH shared secrets
# One set of secrets from sender/receiver (zs), the second set from ephemeral sender/receiver (ze)
def derive1PU(ze, zs, alg, apu, apv, keydatalen):

    z = ze + zs
    key = ConcatKDF(z, alg, apu, apv, keydatalen)
    return key


# The sender generates two shared secrets (ze, zs)
def deriveSender1PU(
    senderEphemeralPriv, senderPriv, recvPub, alg, apu, apv, keydatalen
):

    ze = DeriveECDHSecret(senderEphemeralPriv, recvPub)
    zs = DeriveECDHSecret(senderPriv, recvPub)

    key = derive1PU(ze, zs, alg, apu, apv, keydatalen)
    return key


# The receiver generates two shared secrets (ze, zs)
def deriveReceiver1PU(
    senderEphemeralPub, senderPub, recvPriv, alg, apu, apv, keydatalen
):

    ze = DeriveECDHSecret(recvPriv, senderEphemeralPub)
    zs = DeriveECDHSecret(recvPriv, senderPub)

    key = derive1PU(ze, zs, alg, apu, apv, keydatalen)

    return key
