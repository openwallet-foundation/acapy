@RFC0586
Feature: RFC 0586 Aries sign (endorse) transactions functions

   @T001-RFC0586
   Scenario Outline: endorse a transaction and write to the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
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
         | Acme_capabilities         | Bob_capabilities          | Schema_name    |
         | --did-exchange            | --did-exchange            | driverslicense |
         | --mediation               | --mediation               | driverslicense |
         | --multitenant             | --multitenant             | driverslicense |
         | --mediation --multitenant | --mediation --multitenant | driverslicense |
         | --multitenant --multi-ledger | --multitenant --multi-ledger | driverslicense |
         | --multitenant --multi-ledger --revocation | --multitenant --multi-ledger --revocation | driverslicense |


   @T001.1-RFC0586 @GHA
   Scenario Outline: endorse a transaction and write to the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
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
         | Acme_capabilities         | Bob_capabilities          | Schema_name    |
         |                           |                           | driverslicense |


   @T002-RFC0586
   Scenario Outline: endorse a schema and cred def transaction, write to the ledger, issue and revoke a credential, manually invoking each endorsement endpoint
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets endorser info
      And "Bob" has a DID with role "AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" authors a revocation registry definition transaction for the credential definition matching <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has activated the tails file, and uploaded it to the tails server
      And "Bob" authors a revocation registry entry transaction for the credential definition matching <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Acme" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme" can verify the credential from "Bob" was revoked

      Examples:
         | Acme_capabilities                                   | Bob_capabilities                          | Schema_name    | Credential_data          |
         | --revocation --public-did --did-exchange            | --revocation --did-exchange               | driverslicense | Data_DL_NormalizedValues |
         | --revocation --public-did --mediation               | --revocation --mediation                  | driverslicense | Data_DL_NormalizedValues |
         | --revocation --public-did --multitenant             | --revocation --multitenant                | driverslicense | Data_DL_NormalizedValues |
         | --revocation --public-did --mediation --multitenant | --revocation --mediation --multitenant    | driverslicense | Data_DL_NormalizedValues |
         | --multitenant --multi-ledger --revocation --public-did | --multitenant --multi-ledger --revocation | driverslicense | Data_DL_NormalizedValues |

   @T002.1-RFC0586 @GHA
   Scenario Outline: endorse a schema and cred def transaction, write to the ledger, issue and revoke a credential, manually invoking each endorsement endpoint
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets endorser info
      And "Bob" has a DID with role "AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" authors a revocation registry definition transaction for the credential definition matching <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has activated the tails file, and uploaded it to the tails server
      And "Bob" authors a revocation registry entry transaction for the credential definition matching <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      And "Bob" can write the transaction to the ledger
      And "Acme" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme" can verify the credential from "Bob" was revoked

      Examples:
         | Acme_capabilities                                   | Bob_capabilities                          | Schema_name    | Credential_data          |
         | --revocation --public-did                           | --revocation                              | driverslicense | Data_DL_NormalizedValues |

   @T003-RFC0586
   Scenario Outline: endorse a schema and cred def transaction, write to the ledger, issue and revoke a credential, with auto endorsing workflow
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets endorser info
      And "Bob" has a DID with role "AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme" can verify the credential from "Bob" was revoked

      Examples:
         | Acme_capabilities                                                            | Bob_capabilities                                              | Schema_name    | Credential_data          |
         | --endorser-role endorser --revocation --public-did --did-exchange            | --endorser-role author --revocation --did-exchange            | driverslicense | Data_DL_NormalizedValues |
         | --endorser-role endorser --revocation --public-did --mediation               | --endorser-role author --revocation --mediation               | driverslicense | Data_DL_NormalizedValues |
         | --endorser-role endorser --revocation --public-did --multitenant             | --endorser-role author --revocation --multitenant             | driverslicense | Data_DL_NormalizedValues |
         | --endorser-role endorser --revocation --public-did --mediation --multitenant | --endorser-role author --revocation --mediation --multitenant | driverslicense | Data_DL_NormalizedValues |

   @T003.1-RFC0586 @GHA
   Scenario Outline: endorse a schema and cred def transaction, write to the ledger, issue and revoke a credential, with auto endorsing workflow
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets endorser info
      And "Bob" has a DID with role "AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme" can verify the credential from "Bob" was revoked

      Examples:
         | Acme_capabilities                                   | Bob_capabilities                          | Schema_name    | Credential_data          |
         | --endorser-role endorser --revocation --public-did  | --endorser-role author --revocation       | driverslicense | Data_DL_NormalizedValues |

@T004-RFC0586 @GHA
   Scenario Outline: Select different write ledgers, endorse a schema and cred def transaction, write to the selected ledger, issue and revoke a credential, with auto endorsing workflow
      Given we have "3" agents
         | name  | role                                 | capabilities         |
         | Acme1 | endorser connected with dev bcovrin  | <Acme1_capabilities> |
         | Acme2 | endorser connected with test bcovrin | <Acme2_capabilities> |
         | Bob   | author                               | <Bob_capabilities>   |
      And "Acme1" and "Bob" have an existing connection
      When "Acme1" has a DID with role "ENDORSER"
      And "Acme1" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets "CftsUq2Pmjz3MEmfu8RxUs" and "endorser_dev" as endorser info
      And "Acme2" and "Bob" have an existing connection
      When "Acme2" has a DID with role "ENDORSER"
      And "Acme2" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" connection sets "8FWsRpoLKiuqBNDxik2trg" and "endorser_test" as endorser info
      And "Bob" selects "bcovrinTest" write_ledger, create local wallet did, register on ledger and set as public
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme2" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme2" can verify the credential from "Bob" was revoked
      And "Bob" selects "bcovrinDev" write_ledger, create local wallet did, register on ledger and set as public
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme1" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme1" can verify the credential from "Bob" was revoked
      And "Bob" selects "bcovrinTest" write_ledger, create local wallet did, register on ledger and set as public
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme2" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme2" can verify the credential from "Bob" was revoked
      And "Bob" selects "bcovrinDev" write_ledger, create local wallet did, register on ledger and set as public
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" has written the schema <Schema_name> to the ledger
      And "Bob" authors a credential definition transaction with <Schema_name>
      And "Bob" has written the credential definition for <Schema_name> to the ledger
      And "Bob" has written the revocation registry definition to the ledger
      And "Bob" has written the revocation registry entry transaction to the ledger
      And "Acme1" has an issued <Schema_name> credential <Credential_data> from "Bob"
      And "Bob" revokes the credential without publishing the entry
      And "Bob" authors a revocation registry entry publishing transaction
      Then "Acme1" can verify the credential from "Bob" was revoked

      Examples:
         | Acme1_capabilities                                                                                                                                      | Acme2_capabilities                                                                                                                                       | Bob_capabilities                                                                                                     | Schema_name    | Credential_data          |
         | --endorser-role endorser --revocation --public-did --genesis-url http://dev.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000001             | --endorser-role endorser --revocation --public-did --genesis-url http://test.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000002             | --multitenant --multi-ledger --endorser-role author --revocation --seed bdd_seed_00000000000000000000003             | driverslicense | Data_DL_NormalizedValues |
         | --endorser-role endorser --revocation --public-did --genesis-url http://dev.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000001             | --endorser-role endorser --revocation --public-did --genesis-url http://test.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000002             | --multi-ledger --endorser-role author --revocation --seed bdd_seed_00000000000000000000003                           | driverslicense | Data_DL_NormalizedValues |
         | --mediation --endorser-role endorser --revocation --public-did --genesis-url http://dev.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000001 | --mediation --endorser-role endorser --revocation --public-did --genesis-url http://test.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000002 | --multi-ledger --mediation --endorser-role author --revocation --seed bdd_seed_00000000000000000000003               | driverslicense | Data_DL_NormalizedValues |
         | --mediation --endorser-role endorser --revocation --public-did --genesis-url http://dev.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000001 | --mediation --endorser-role endorser --revocation --public-did --genesis-url http://test.bcovrin.vonx.io/genesis --seed bdd_seed_00000000000000000000002 | --multitenant --mediation --multi-ledger --endorser-role author --revocation --seed bdd_seed_00000000000000000000003 | driverslicense | Data_DL_NormalizedValues |
