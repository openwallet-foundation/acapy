Feature: RFC 0586 Aries sign (endorse) transactions functions

   @T001-RFC0586 @GHA
   Scenario Outline: endorse a transaction and write to the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Bob" has a DID with role "AUTHOR"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      Then "Bob" can write the transaction to the ledger
      And "Bob" has written the schema <Schema_name> to the ledger

      Examples:
         | Acme_capabilities        | Bob_capabilities       | Schema_name    |
         |                          |                        | driverslicense |
         | --did-exchange           | --did-exchange         | driverslicense |
         | --mediation              | --mediation            | driverslicense |
         | --multitenant            | --multitenant          | driverslicense |

   @T001.1-RFC0586
   Scenario Outline: endorse a transaction and write to the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Bob" has a DID with role "AUTHOR"
      And "Acme" connection has job role "TRANSACTION_ENDORSER"
      And "Bob" connection has job role "TRANSACTION_AUTHOR"
      And "Bob" authors a schema transaction with <Schema_name>
      And "Bob" requests endorsement for the transaction
      And "Acme" endorses the transaction
      Then "Bob" can write the transaction to the ledger
      And "Bob" has written the schema <Schema_name> to the ledger

      Examples:
         | Acme_capabilities          | Bob_capabilities             | Schema_name    |
         | --mediation --multitenant  | --mediation --multitenant    | driverslicense |
