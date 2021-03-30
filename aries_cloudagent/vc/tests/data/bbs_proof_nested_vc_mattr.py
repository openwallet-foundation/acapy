BBS_PROOF_NESTED_VC_MATTR = {
    "@context": [
        "https://www.w3.org/2018/credentials/v1",
        "https://www.w3.org/2018/credentials/examples/v1",
        "https://w3id.org/security/bbs/v1",
    ],
    "id": "https://example.gov/credentials/3732",
    "type": ["UniversityDegreeCredential", "VerifiableCredential"],
    "credentialSubject": {
        "id": "did:example:489398593",
        "college": "Contoso University",
        "degree": {
            "id": "urn:bnid:_:c14n0",
            "type": "BachelorDegree",
            "name": "Bachelor of Science and Arts",
            "degreeType": "Underwater Basket Weaving",
        },
    },
    "issuanceDate": "2020-03-10T04:24:12.164Z",
    "proof": {
        "type": "BbsBlsSignatureProof2020",
        "created": "2020-12-14T03:11:30Z",
        "nonce": "CF69iO3nfvqRsRBNElE8b4wO39SyJHPM7Gg1nExltW5vSfQA1lvDCR/zXX1To0/4NLo=",
        "proofPurpose": "assertionMethod",
        "proofValue": "AA0f/7dHROgM2jXZiK0UmY5956/26qbbWF1sKgTMLx1NWEJqrE2ptwlREsxxrqZDRy5pxIFeSxDe08yWxDIk7zefzbwHd04hfbs0oaE2e9TMxIhfUZnct5Br7XenOwpZkkW1d7nt/yUFclgLCAIg+8B3UDpsuzv4rAJ3bTvD69nrMJPwC+Ao7meBgPcAaubNirSqrgAAAHSqzxvoLIRtX8mcq90yIHHuAcThiP63ChKE9c49pJboQ5FBA1aiMIIAJ+J7JPZtBGUAAAACIly7gNiA2nXJAVTKNepEQOtdyEU1gqExcaxWhMgX6nBCRGCwypy5lDDj2XWsvcuzPcvrpvaBxIBvTBAVjKDODaExOe1FKwA2t6F80wvt1BrEQpa5mG9YsI7Hw0wwl+c0SekC/WYlVW0oFjdICH+ZsAAAAAJlYX1Br69N/IAemIkmBvU/7bcIGssDcGL4hNzuTe0a8FnXYhUHyYmnMYFgZMv2ht2nMZiSwAugP2y3dFAU99bU",
        "verificationMethod": "did:example:489398593#test",
    },
}
