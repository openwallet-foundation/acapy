Feature: RFC 0160 Aries agent connection functions

   @T001-RFC0160
   Scenario Outline: establish a connection between two agents
      Given we have "2" agents
         | name  | role    | capabilities        | extra        |
         | Acme  | inviter | <Acme_capabilities> | <Acme_extra> |
         | Bob   | invitee | <Bob_capabilities>  | <Bob_extra>  |
      When "Acme" generates a connection invitation
      And "Bob" receives the connection invitation
      Then "Acme" has an active connection
      And "Bob" has an active connection

      @GHA @UnqualifiedDids
      Examples:
         | Acme_capabilities           | Acme_extra        | Bob_capabilities | Bob_extra        |
         | --public-did --did-exchange | --emit-did-peer-2 | --did-exchange   |--emit-did-peer-2 |
         | --public-did --did-exchange | --emit-did-peer-4 | --did-exchange   |--emit-did-peer-4 |
         | --public-did --did-exchange | --emit-did-peer-2 | --did-exchange   |--emit-did-peer-4 |
         | --public-did --did-exchange | --emit-did-peer-4 | --did-exchange   |--emit-did-peer-2 |
         | --public-did --did-exchange --reuse-connections | --emit-did-peer-2 | --did-exchange   |--emit-did-peer-4 |
         | --public-did --did-exchange --reuse-connections | --emit-did-peer-4 | --did-exchange   |--emit-did-peer-2 |
