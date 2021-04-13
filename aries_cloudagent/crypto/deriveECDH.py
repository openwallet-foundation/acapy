from ecdsa import ECDH, NIST256p, SigningKey

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.concatkdf import ConcatKDFHash
from cryptography.hazmat.backends import default_backend

from binascii import unhexlify

# Generate a shared secret from your private key and a received public key (keys are in Byte format)
def DeriveECDHSecret(privateKey, publicKey):

    derive = ECDH(curve=NIST256p)
    derive.load_private_key_bytes(unhexlify(privateKey))
    derive.load_received_public_key_bytes(unhexlify(publicKey))

    secret = derive.generate_sharedsecret_bytes()

    # secret = derive.generate_sharedsecret()

    return secret

# Generate a shared secret from your private key and a received public key (keys are in Key object format)
def DeriveECDHSecretFromKey(privateKey, publicKey):

    derive = ECDH(curve=NIST256p)
    derive.load_private_key(privateKey)
    derive.load_received_public_key(publicKey)

    secret = derive.generate_sharedsecret_bytes()

    # secret - derive.generate_sharedsecret()

    return secret

# Generate a shared encryption key from a ECDH generated shared secret
def ConcatKDF(sharedSecret, otherinfo= b"alg_id + apu_info + apv_info + pub_info"):

    ckdf = ConcatKDFHash(
        algorithm = hashes.SHA256(),
        length = 32,
        otherinfo = otherinfo,
        backend = default_backend()
    )
    sharedKey = ckdf.derive(sharedSecret)

    ckdf = ConcatKDFHash(
        algorithm = hashes.SHA256(),
        length = 32,
        otherinfo = otherinfo,
        backend = default_backend()
    )
    ckdf.verify(sharedSecret, sharedKey)

    return sharedKey