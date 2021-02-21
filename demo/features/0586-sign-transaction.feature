Feature: RFC 0586 Aries sign (endorse) transactions functions

   @T001-RFC0586 @P1 @critical @AcceptanceTest @RFC0586
   Scenario Outline: endorse a transaction and write to the ledger
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Acme  | endorser | <Acme_capabilities> |
         | Bob   | author   | <Bob_capabilities>  |
      And "Acme" and "Bob" have an existing connection
      When "Acme" has a DID with role "ENDORSER"
      And "Bob" has a DID with role "AUTHOR"
      And "Acme" connection has job role "TXN_ENDORSER"
      And "Bob" connection has job role "TXN_AUTHOR"

      Examples:
         | Acme_capabilities         | Bob_capabilities          |
         |                           |                           |
