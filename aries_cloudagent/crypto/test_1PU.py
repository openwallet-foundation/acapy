from derive1PU import *
from ecdsa import ECDH, NIST256p, SigningKey

def Test_Generate1PUKey():

    aliceSecretKey = "23832cbef38641b8754a35f1f79bbcbc248e09ac93b01c2eaf12474f2ac406b6"
    alicePublicKey = "04fd4ca9eb7954a03517ac8249e6070aa3112e582f596b10f0d45d757b56d5dc0395a7d207d06503a4d6ad6e2ad3a1fd8cc233c072c0dc0f32213deb712c32cbdf"

    bobSecretKey = "2d1b242281944aa58c251ce12db6df8babd703b5c0a1fc0b9a34f5b7b9ad6030"
    bobPublicKey = "04e35cde5e3761d075fc87b3b0983a179e1b8e09da242e79965d657cba48f792dfc9b446a098ab0194888cd9d53a21c873c00264275dba925c2db6c458c87ca3d6"

    aliceEphemeralSecretKey = "b5b1158f6fba847407853cdf4bfbcf120412e25918eb15d5a1e7fe04570f6907"
    aliceEphemeralPublicKey = "04bf4e51d403a9cdfcfa2fe38abf6229db33f59ac14395e92f5b353af213391484f017d3d336f4e03ca974285722641be48d98d5589104ab99abe702fb2bfa6fe2"

    aliceKey = deriveSender1PU(aliceEphemeralSecretKey, aliceSecretKey, bobPublicKey)
    print("Alice 1PU key: ", aliceKey)
    bobKey = deriveReceiver1PU(aliceEphemeralPublicKey, alicePublicKey, bobSecretKey)
    print("Bob 1PU key: ", bobKey)

    assert aliceKey == bobKey, "Both parties should generate the same key using ECDH-1PU"

def main():
    
    Test_Generate1PUKey()


if __name__ == "__main__":
    main()
    print("All tests passed")