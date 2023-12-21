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
         | --public-did --did-exchange | --emit-did-peer-2 | --did-exchange   |                  |

      @GHA @WalletType_Askar
      Examples:
         | Acme_capabilities                                 | Acme_extra | Bob_capabilities                     | Bob_extra |
         | --public-did                                      |            |                                      |           |
         | --public-did --did-exchange                       |            | --did-exchange                       |           |
         | --public-did --mediation                          |            | --mediation                          |           |
         | --public-did --multitenant                        |            | --multitenant                        |           |
         | --public-did --mediation --multitenant --log-file |            | --mediation --multitenant --log-file |           |

      @GHA @WalletType_Askar_AnonCreds
      Examples:
         | Acme_capabilities                                         | Acme_extra | Bob_capabilities                              | Bob_extra | 
         | --public-did --wallet-type askar-anoncreds                |            | --wallet-type askar-anoncreds                 |           |
         | --public-did --wallet-type askar-anoncreds                |            |                                               |           |
         | --public-did                                              |            | --wallet-type askar-anoncreds                 |           |
         | --public-did --did-exchange --wallet-type askar-anoncreds |            | --did-exchange --wallet-type askar-anoncreds  |           |
         | --public-did --mediation --wallet-type askar-anoncreds    |            | --mediation --wallet-type askar-anoncreds     |           |
         | --public-did --multitenant --wallet-type askar-anoncreds  |            | --multitenant --wallet-type askar-anoncreds   |           |
