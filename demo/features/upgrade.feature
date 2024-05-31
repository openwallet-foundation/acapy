Feature: ACA-Py Anoncreds Upgrade

   @PR @Release
   Scenario Outline: Using revocation api, issue, revoke credentials and publish
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "<issuer>" has written the credential definition for <Schema_name> to the ledger
      And "<issuer>" has written the revocation registry definition to the ledger
      And "<issuer>" has written the revocation registry entry transaction to the ledger
      And "<issuer>" revokes the credential without publishing the entry
      And "<issuer>" authors a revocation registry entry publishing transaction
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail
      Then "Bob" can verify the credential from "<issuer>" was revoked
      And "<issuer>" upgrades the wallet to anoncreds
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Bob" upgrades the wallet to anoncreds
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"

      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --revocation --public-did --multitenant | --multitenant       | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |