Feature: RFC 0160 Aries agent connection functions

   @T001-AIP10-RFC0160 @P1 @critical @AcceptanceTest @RFC0160
   Scenario Outline: establish a connection between two agents
      Given we have "2" agents
         | name  | role    | capabilities        |
         | Acme  | inviter | <Acme_capabilities> |
         | Bob   | invitee | <Bob_capabilties>   |
      When "Acme" generates a connection invitation
      And "Bob" receives the connection invitation
      And "Bob" sends a connection request to "Acme"
      And "Acme" receives the connection request
      And "Acme" sends a connection response to "Bob"
      And "Bob" receives the connection response
      And "Bob" sends <message> to "Acme"
      Then "Acme" and "Bob" have a connection

      Examples:
         | message   | Acme_capabilities   | Bob_capabilities   |
         | trustping |                     |                    |
         | trustping | --mediation         | --mediation        |
