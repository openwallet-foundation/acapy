Feature: TAA Transaction Author Agreement related tests

# Note that these tests require a ledger with TAA enabled
# you can run von-network as `./manage start --taa-sample --logs`

   @T001-TAA @taa_required
   Scenario Outline: accept the ledger TAA and write to the ledger
      Given we have "1" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
      And "Acme" connects to a ledger that requires acceptance of the TAA
      When "Acme" accepts the TAA
      Then "Acme" is ready to issue a credential for <Schema_name>

      Examples:
         | Acme_capabilities                      | Schema_name    |
         | --taa-accept                           | driverslicense |
         | --taa-accept --multitenant             | driverslicense |
         | --taa-accept --revocation              | driverslicense |
         | --taa-accept --multi-ledger            | driverslicense |
         | --taa-accept --multitenant --multi-ledger | driverslicense |

   @T001a-TAA @taa_required
   Scenario Outline: accept the ledger TAA and write to the ledger via endorser
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" connects to a ledger that requires acceptance of the TAA
      And "Bob" connects to a ledger that requires acceptance of the TAA
      And "Acme" and "Bob" have an existing connection
      When "Acme" accepts the TAA
      And "Bob" accepts the TAA
      And "Acme" has a DID with role "ENDORSER"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets endorser info
      And "Bob" has a DID with role "AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      Then "Bob" can write the transaction to the ledger
      And "Bob" has written the schema <Schema_name> to the ledger

      Examples:
         | Acme_capabilities          | Bob_capabilities           | Schema_name    |
         | --taa-accept               | --taa-accept               | driverslicense |
         | --taa-accept --multitenant | --taa-accept --multitenant | driverslicense |

   @T002-TAA @taa_required
   Scenario Outline: Revoke credential using a ledger with TAA required
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T003-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      Then "Faber" accepts the TAA
      And "Faber" posts a revocation correction to the ledger
      And "Faber" successfully revoked the credential
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T004-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger authomatically with the next revoked credential
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" accepts the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T004.0-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger manually before revoking more credentials
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" accepts the TAA
      Then "Faber" posts a revocation correction to the ledger
      And "Faber" successfully revoked the credential
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T004.1-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger by manually applying a correction
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" accepts the TAA
      Then "Faber" posts a revocation correction to the ledger
      And "Faber" successfully revoked the credential
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T004.2-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger automatically with the next revocation
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" accepts the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T004.5-TAA @taa_required
   Scenario Outline: Fail to publish revoked credential using a ledger with TAA required, and fix the ledger authomatically by revoking the last credential
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "Faber" connects to a ledger that requires acceptance of the TAA
      And "Faber" accepts the TAA
      And "Faber" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential
      When "Faber" rejects the TAA
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Faber" accepts the TAA
      And "Faber" attempts to revoke the credential
      And "Faber" fails to publish the credential revocation
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" revokes the credential
      And "Faber" successfully revoked the credential

      Examples:
         | issuer | Acme_capabilities                        | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --taa-accept --revocation --public-did   |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
