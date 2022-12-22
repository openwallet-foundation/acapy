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
      Given we have "3" agents
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

   @T003-RFC0454.1 @GHA
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, neither credential is revoked
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |

   @T003-RFC0454.1f
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, neither credential is revoked, fails due to requesting request-level revocation
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_r2 |

   @T003-RFC0454.2 @GHA
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, and the revocable credential is revoked, and the proof checks for revocation and fails
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer1>" revokes the credential
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_r2 |

   @T003-RFC0454.3 @GHA
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, and the revocable credential is revoked, and the proof doesn't check for revocation and passes
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer1>" revokes the credential
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request with explicit revocation status for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                             |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_no_revoc |
