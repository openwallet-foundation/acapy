from binascii import unhexlify

from .....wallet.util import b64_to_bytes

from ..derive_1pu import *


def test_1pu_hex_example():
    # Previously randomly generated 3 sets of keys
    aliceSecretKey = "23832cbef38641b8754a35f1f79bbcbc248e09ac93b01c2eaf12474f2ac406b6"
    alicePublicKey = "04fd4ca9eb7954a03517ac8249e6070aa3112e582f596b10f0d45d757b56d5dc0395a7d207d06503a4d6ad6e2ad3a1fd8cc233c072c0dc0f32213deb712c32cbdf"

    bobSecretKey = "2d1b242281944aa58c251ce12db6df8babd703b5c0a1fc0b9a34f5b7b9ad6030"
    bobPublicKey = "04e35cde5e3761d075fc87b3b0983a179e1b8e09da242e79965d657cba48f792dfc9b446a098ab0194888cd9d53a21c873c00264275dba925c2db6c458c87ca3d6"

    aliceEphemeralSecretKey = (
        "b5b1158f6fba847407853cdf4bfbcf120412e25918eb15d5a1e7fe04570f6907"
    )
    aliceEphemeralPublicKey = "04bf4e51d403a9cdfcfa2fe38abf6229db33f59ac14395e92f5b353af213391484f017d3d336f4e03ca974285722641be48d98d5589104ab99abe702fb2bfa6fe2"

    # Header parameters used in ConcatKDF
    alg = "A256GCM"
    apu = "Alice"
    apv = "Bob"
    keydatalen = 32  # 32 bytes or 256 bit output key length

    aliceKey = derive_sender_1pu(
        aliceEphemeralSecretKey, aliceSecretKey, bobPublicKey, alg, apu, apv, keydatalen
    )
    print("Alice 1PU key: ", aliceKey.hex())
    bobKey = derive_receiver_1pu(
        aliceEphemeralPublicKey, alicePublicKey, bobSecretKey, alg, apu, apv, keydatalen
    )
    print("Bob 1PU key: ", bobKey.hex())

    assert (
        aliceKey == bobKey
    ), "Both parties should generate the same key using ECDH-1PU"


# Example key exchange in https://tools.ietf.org/id/draft-madden-jose-ecdh-1pu-03.html#rfc.appendix.A
def test_1pu_appendix_example():
    # Convert the three JWK keys into hex encoded byte format

    # Alice Key
    d = "Hndv7ZZjs_ke8o9zXYo3iq-Yr8SewI5vrqd0pAvEPqg"
    x = "WKn-ZIGevcwGIyyrzFoZNBdaq9_TsqzGl96oc0CWuis"
    y = "y77t-RvAHRKTsSGdIYUfweuOvwrvDD-Q3Hv5J0fSKbE"

    aliceSecretKey = b64_to_bytes(d, urlsafe=True).hex()
    alicePublicKey = (
        b64_to_bytes(x, urlsafe=True) + b64_to_bytes(y, urlsafe=True)
    ).hex()

    # _______________________________________________________________________________

    # Bob key
    d = "VEmDZpDXXK8p8N0Cndsxs924q6nS1RXFASRl6BfUqdw"
    x = "weNJy2HscCSM6AEDTDg04biOvhFhyyWvOHQfeF_PxMQ"
    y = "e8lnCO-AlStT-NJVX-crhB7QRYhiix03illJOVAOyck"

    bobSecretKey = b64_to_bytes(d, urlsafe=True).hex()
    bobPublicKey = (b64_to_bytes(x, urlsafe=True) + b64_to_bytes(y, urlsafe=True)).hex()

    # _______________________________________________________________________________

    # Alice Ephemeral Key
    d = "0_NxaRPUMQoAJt50Gz8YiTr8gRTwyEaCumd-MToTmIo"
    x = "gI0GAILBdu7T53akrFmMyGcsF3n5dO7MmwNBHKW5SV0"
    y = "SLW_xSffzlPWrHEVI30DHM_4egVwt3NQqeUD7nMFpps"

    aliceEphemeralSecretKey = b64_to_bytes(d, urlsafe=True).hex()
    aliceEphemeralPublicKey = (
        b64_to_bytes(x, urlsafe=True) + b64_to_bytes(y, urlsafe=True)
    ).hex()

    # _______________________________________________________________________________

    # Header parameters used in ConcatKDF
    alg = "A256GCM"
    apu = "Alice"
    apv = "Bob"
    keydatalen = 32  # 32 bytes or 256 bit output key length

    aliceKey = derive_sender_1pu(
        aliceEphemeralSecretKey, aliceSecretKey, bobPublicKey, alg, apu, apv, keydatalen
    )
    print("Alice 1PU key: ", aliceKey.hex())
    bobKey = derive_receiver_1pu(
        aliceEphemeralPublicKey, alicePublicKey, bobSecretKey, alg, apu, apv, keydatalen
    )
    print("Bob 1PU key: ", bobKey.hex())

    expected_result = unhexlify(
        "6caf13723d14850ad4b42cd6dde935bffd2fff00a9ba70de05c203a5e1722ca7"
    )

    assert (
        aliceKey == bobKey
    ), "Both parties should generate the same key using ECDH-1PU"
    assert (
        aliceKey == expected_result
    ), "Generated key should match the appendix A example"


def main():
    test_1pu_hex_example()
    test_1pu_appendix_example()


if __name__ == "__main__":
    main()
    print("All tests passed")
