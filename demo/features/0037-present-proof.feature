Feature: RFC 0037 Aries agent present proof

   @T001-AIP10-RFC0037 @P1 @critical @AcceptanceTest @Indy @RFC0037
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given "3" agents
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
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name    | Credential_data          | Proof_request  |
         | Acme   | --public-did                           |                           | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
         | Faber  | --public-did                           |                           | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
         | Acme   | --public-did --did-exchange            | --did-exchange            | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
         | Acme   | --public-did --mediation               | --mediation               | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
         | Acme   | --public-did --multitenant             | --multitenant             | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
         | Acme   | --public-did --mediation --multitenant | --mediation --multitenant | driverslicense | Data_DL_NormalizedValues | DL_age_over_19 |
