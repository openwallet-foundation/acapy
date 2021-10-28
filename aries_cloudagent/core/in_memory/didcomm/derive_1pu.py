"""Functions for performing Key Agreement using ECDH-1PU."""

from .derive_ecdh import derive_shared_secret, concat_kdf


def derive_1pu(ze, zs, alg, apu, apv, keydatalen):
    """Generate shared encryption key from two ECDH shared secrets."""

    z = ze + zs
    key = concat_kdf(z, alg, apu, apv, keydatalen)
    return key


def derive_sender_1pu(epk, sender_sk, recip_pk, alg, apu, apv, keydatalen):
    """Generate two shared secrets (ze, zs)."""

    ze = derive_shared_secret(epk, recip_pk)
    zs = derive_shared_secret(sender_sk, recip_pk)

    key = derive_1pu(ze, zs, alg, apu, apv, keydatalen)
    return key


def derive_receiver_1pu(epk, sender_pk, recip_sk, alg, apu, apv, keydatalen):
    """Generate two shared secrets (ze, zs)."""

    ze = derive_shared_secret(recip_sk, epk)
    zs = derive_shared_secret(recip_sk, sender_pk)

    key = derive_1pu(ze, zs, alg, apu, apv, keydatalen)

    return key
