@RFC0160
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

      @PR @Release @UnqualifiedDids
      Examples:
         | Acme_capabilities                               | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --public-did --did-exchange --emit-did-peer-2                     | | --did-exchange --emit-did-peer-2                     | |
         | --public-did --did-exchange --emit-did-peer-4                     | | --did-exchange --emit-did-peer-4                     | |
         | --public-did --did-exchange --reuse-connections --emit-did-peer-4 | | --did-exchange --reuse-connections --emit-did-peer-4 | |

      @UnqualifiedDids
      Examples:
         | Acme_capabilities                               | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --public-did --did-exchange --emit-did-peer-2                     | | --did-exchange --emit-did-peer-4                     | |
         | --public-did --did-exchange --reuse-connections --emit-did-peer-4 | | --did-exchange --reuse-connections --emit-did-peer-2 | |
         | --public-did --did-exchange --emit-did-peer-4                     | | --did-exchange --emit-did-peer-2                     | |

      @PublicDidReuse
      Examples:
         | Acme_capabilities                               | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --public-did --did-exchange                     |                   | --did-exchange                     |                   |
         | --public-did --did-exchange --reuse-connections |                   | --did-exchange --reuse-connections |                   |

      @DidPeerConnectionReuse
      Examples:
         | Acme_capabilities                               | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --did-exchange --emit-did-peer-2                                  | | --emit-did-peer-2                                    | |
         | --did-exchange --reuse-connections --emit-did-peer-2              | | --reuse-connections --emit-did-peer-2                | |
         | --did-exchange --emit-did-peer-4                                  | | --emit-did-peer-4                                    | |
         | --did-exchange --reuse-connections --emit-did-peer-4              | | --reuse-connections --emit-did-peer-4                | |

      @PR @Release @MultiUseConnectionReuse
      Examples:
         | Acme_capabilities                                                       | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --did-exchange --multi-use-invitations --emit-did-peer-2                                  | | --emit-did-peer-2                                    | |
         | --did-exchange --multi-use-invitations --reuse-connections --emit-did-peer-4              | | --reuse-connections --emit-did-peer-4                | |
         | --public-did --did-exchange --multi-use-invitations --emit-did-peer-2                     | | --did-exchange --emit-did-peer-4                     | |
         | --public-did --did-exchange --multi-use-invitations --reuse-connections --emit-did-peer-4 | | --did-exchange --reuse-connections --emit-did-peer-2 | |

      @MultiUseConnectionReuse
      Examples:
         | Acme_capabilities                                                       | Acme_extra        | Bob_capabilities                   | Bob_extra         |
         | --did-exchange --multi-use-invitations --reuse-connections --emit-did-peer-2              | | --reuse-connections --emit-did-peer-2                | |
         | --did-exchange --multi-use-invitations --emit-did-peer-4                                  | | --emit-did-peer-4                                    | |
         | --public-did --did-exchange --multi-use-invitations --emit-did-peer-4                     | | --did-exchange --emit-did-peer-2                     | |
         | --public-did --did-exchange --multi-use-invitations --reuse-connections --emit-did-peer-2 | | --did-exchange --reuse-connections --emit-did-peer-4 | |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | Acme_capabilities                                                             | Acme_extra        | Bob_capabilities                                                 | Bob_extra         |
         | --public-did --did-exchange --wallet-type askar-anoncreds --emit-did-peer-2                     | | --did-exchange --wallet-type askar-anoncreds --emit-did-peer-2                     | |
         | --public-did --did-exchange --wallet-type askar-anoncreds --reuse-connections --emit-did-peer-4 | | --did-exchange --wallet-type askar-anoncreds --reuse-connections --emit-did-peer-4 | |
         | --did-exchange --wallet-type askar-anoncreds --emit-did-peer-2                                  | | --wallet-type askar-anoncreds --emit-did-peer-2                                    | |
         | --did-exchange --wallet-type askar-anoncreds --reuse-connections --emit-did-peer-4              | | --wallet-type askar-anoncreds --reuse-connections --emit-did-peer-4                | |
