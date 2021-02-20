Feature: RFC 0036 Aries agent issue credential

  @T003-RFC0036 @AcceptanceTest @P1 @critical @Indy @RFC0036
  Scenario Outline: Issue a credential with the Issuer beginning with an offer
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Acme" is ready to issue a credential for <Schema_name>
    When "Acme" offers a credential with data <Credential_data>
    Then "Bob" has the credential issued

    Examples:
       | Acme_capabilities                      | Bob_capabilities          | Schema_name    | Credential_data          |
       | --public-did                           |                           | driverslicense | Data_DL_NormalizedValues |
       | --public-did --did-exchange            | --did-exchange            | driverslicense | Data_DL_NormalizedValues |
       | --public-did --mediation               | --mediation               | driverslicense | Data_DL_NormalizedValues |
       | --public-did --multitenant             | --multitenant             | driverslicense | Data_DL_NormalizedValues |
       | --public-did --mediation --multitenant | --mediation --multitenant | driverslicense | Data_DL_NormalizedValues |


  @T004-RFC0036 @AcceptanceTest @P1 @critical @Indy @RFC0036
  Scenario Outline: Issue a credential with revocation, with the Issuer beginning with an offer, and then revoking the credential
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Bob" has an issued <Schema_name> credential <Credential_data> from "Acme"
    Then "Acme" revokes the credential
    Then "Bob" has the credential issued

    Examples:
       | Acme_capabilities                        | Bob_capabilities  | Schema_name    | Credential_data          |
       | --revocation --public-did                |                   | driverslicense | Data_DL_NormalizedValues |
       | --revocation --public-did --did-exchange | --did-exchange    | driverslicense | Data_DL_NormalizedValues |
       | --revocation --public-did --mediation    | --mediation       | driverslicense | Data_DL_NormalizedValues |
       | --revocation --public-did --multitenant  | --multitenant     | driverslicense | Data_DL_NormalizedValues |
