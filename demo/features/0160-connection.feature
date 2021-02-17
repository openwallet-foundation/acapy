Feature: RFC 0160 Aries agent connection functions

   @T001-AIP10-RFC0160 @P1 @critical @AcceptanceTest @RFC0160
   Scenario Outline: establish a connection between two agents
      Given we have "2" agents
         | name  | role    | capabilities        |
         | Acme  | inviter | <Acme_capabilities> |
         | Bob   | invitee | <Bob_capabilities>  |
      When "Acme" generates a connection invitation
      And "Bob" receives the connection invitation
      Then "Acme" has an active connection
      And "Bob" has an active connection

      Examples:
         | Acme_capabilities   | Bob_capabilities   |
         |                     |                    |
         | --mediation         | --mediation        |
         | --multitenant       | --multitenant      |
         | --mediation --multitenant | --mediation --multitenant |
