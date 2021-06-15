Feature: RFC 0454 Aries agent present proof

   @T001-RFC0454 @GHA
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did --did-exchange            | --did-exchange            | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T001.1-RFC0454
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --public-did --mediation --multitenant | --mediation --multitenant | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T001.2-RFC0454 @GHA
   Scenario Outline: Present Proof json-ld where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued json-ld <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for json-ld proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      Examples:
         | issuer | Acme_capabilities                                         | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --public-did --cred-type json-ld                          |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did --cred-type json-ld --did-exchange           | --did-exchange            | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T002-RFC0454 @GHA
   Scenario Outline: Present Proof where the issuer revokes the credential and the proof fails
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "<issuer>" revokes the credential
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --revocation --public-did --did-exchange   | --did-exchange   | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T002.1-RFC0454
   Scenario Outline: Present Proof where the issuer revokes the credential and the proof fails
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "<issuer>" revokes the credential
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --mediation      |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --multitenant    | --multitenant    | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
