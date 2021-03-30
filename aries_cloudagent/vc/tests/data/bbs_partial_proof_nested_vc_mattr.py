BBS_PARTIAL_PROOF_NESTED_VC_MATTR = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["UniversityDegreeCredential", "VerifiableCredential"],
    "credentialSubject": {
        "id": "did:example:489398593",
        "degree": {
            "id": "urn:bnid:_:c14n0",
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts",
        },
    },
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "created": "2020-12-14T03:11:30Z",
        "nonce": "am6ZmHvRRrhDNdiEzfpZm7kBLwlh5B4ULmwczzH9iwtLnMu7QhH9WaWmtEwJ0LrwdpI=",
        "proofPurpose": "assertionMethod",
        "proofValue": "AA0N76Kuc+1HYPajNPxCemRdLGV0q5nUIB0DdOm1nsrbql6JsyM5TzTSBIcG7u6plxPLI7VCrxYQ16u2CjlafhlXXLBvm+ERVPN2i2aPgq+h9Ykb3sVGYEwI34nLDeeMAyo9gbLJoKnFBggaBe0h5uyJLQVefuegsdhAe6/tishSBp8/um9odS+3vMVh9EwNvfVpbAAAAHSHEWi10j8BRaTgvn3KX5R6xS9AdzbHlHt5z3ZcBRnJi9jB1l2BJHR/KypsNT7EJjcAAAACanX0ZNVF4p/SlCS9SY8bGWL4SyEMWfpvacZ/bR8pZG9PVMDZUEPsN1QpjQnekkIWks3ep42r8veuoDwlzQljMLnxGFQ78hwVpzWnAwpur2kR41Gbhq/r2XXwYY3U/tN2VBHHXMOj11YJARAbT4VUmAAAAAUBFdHA3fGTapyNQUZbvwTlWYSTX1ABL1hSTvd5O+a1QHJymaIoOVevNWQCVq+TIlGvcBiJmF0TVFV1DjDgFMFhVRLmw6zEYEMQZkaOv8eRlDbAVZGPtJpZr8GLN6wlfE1GhPwi8iLzYR01Y8sV6dqLtJvSHf8gnqieBJUTT4M9rkgOn/5zM6q4Su6bDUfgMWqlH75tPzxVwMG9Gbw4J+Vt",
        "verificationMethod": "did:example:489398593#test",
    },
}
