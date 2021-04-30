"""Functions for performing Key Agreement using ECDH-1PU."""

from .deriveECDH import DeriveECDHSecret, ConcatKDF


def derive1PU(ze, zs, alg, apu, apv, keydatalen):
    """
    ECDH-1PU generates a shared encryption key from two concatenated ECDH shared secrets
    One set of secrets from sender/receiver (zs)
    Second set from ephemeral sender/receiver (ze)
    """

    z = ze + zs
    key = ConcatKDF(z, alg, apu, apv, keydatalen)
    return key


def deriveSender1PU(
    senderEphemeralPriv, senderPriv, recvPub, alg, apu, apv, keydatalen
):
    """
    The sender generates two shared secrets (ze, zs)
    """

    ze = DeriveECDHSecret(senderEphemeralPriv, recvPub)
    zs = DeriveECDHSecret(senderPriv, recvPub)

    key = derive1PU(ze, zs, alg, apu, apv, keydatalen)
    return key


def deriveReceiver1PU(
    senderEphemeralPub, senderPub, recvPriv, alg, apu, apv, keydatalen
):
    """
    The receiver generates two shared secrets (ze, zs)
    """

    ze = DeriveECDHSecret(recvPriv, senderEphemeralPub)
    zs = DeriveECDHSecret(recvPriv, senderPub)

    key = derive1PU(ze, zs, alg, apu, apv, keydatalen)

    return key
