TEST_LD_DOCUMENT_CORRECT_SCHEMA = {
    "@context": [
            "https://www.w3.org/2018/credentials/v1",
            "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
            "https://purl.imsglobal.org/spec/ob/v3p0/extensions.json"
        ],
        "id": "http://example.edu/credentials/3732",
        "type": ["VerifiableCredential", "OpenBadgeCredential"],
        "issuer": {
            "id": "string",
            "type": [
                "Profile"
            ],
            "name": "Example University"
        },
        "issuanceDate": "2010-01-01T00:00:00Z",
        "name": "Example University Degree",
        "credentialSubject": {
            "type": [
                "AchievementSubject"
            ],
            "achievement": {
                "id": "https://example.com/achievements/21st-century-skills/teamwork",
                "type": [
                    "Achievement"
                ],
                "criteria": {
                    "narrative": "Team members are nominated for this badge by their peers and recognized upon review by Example Corp management."
                },
                "description": "This badge recognizes the development of the capacity to collaborate within a group environment.",
                "name": "Teamwork"
            },
            "creditsEarned": 2.1
        },
        "credentialSchema": [
            {
                "id": "https://purl.imsglobal.org/spec/ob/v3p0/schema/json-ld/ob_v3p0_anyachievementcredential_schema.json",
                "type": "1EdTechJsonSchemaValidator2019"
            }
        ]

}
