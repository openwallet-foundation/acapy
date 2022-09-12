@RFC0453
Feature: RFC 0453 Aries agent issue credential

  @T003-RFC0453 @GHA
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
       #| --public-did --did-exchange            | --did-exchange            | driverslicense | Data_DL_NormalizedValues |
       #| --public-did --mediation               | --mediation               | driverslicense | Data_DL_NormalizedValues |
       #| --public-did --multitenant             | --multitenant             | driverslicense | Data_DL_NormalizedValues |


  @T003.1-RFC0453 @GHA
  Scenario Outline: Issue a json-ld credential with the Issuer beginning with an offer
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Acme" is ready to issue a json-ld credential for <Schema_name>
    And "Bob" is ready to receive a json-ld credential
    When "Acme" offers "Bob" a json-ld credential with data <Credential_data>
    Then "Bob" has the json-ld credential issued

    Examples:
       | Acme_capabilities                                   | Bob_capabilities          | Schema_name    | Credential_data          |
       | --public-did --cred-type json-ld                    |                           | driverslicense | Data_DL_NormalizedValues |
       | --public-did --cred-type json-ld --did-exchange     | --did-exchange            | driverslicense | Data_DL_NormalizedValues |
       | --public-did --cred-type json-ld --mediation        | --mediation               | driverslicense | Data_DL_NormalizedValues |
       | --public-did --cred-type json-ld --multitenant      | --multitenant             | driverslicense | Data_DL_NormalizedValues |


  @T004-RFC0453 @GHA
  Scenario Outline: Issue a credential with revocation, with the Issuer beginning with an offer, and then revoking the credential
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Bob" has an issued <Schema_name> credential <Credential_data> from "Acme"
    Then "Acme" revokes the credential
    And "Bob" has the credential issued

    Examples:
       | Acme_capabilities                        | Bob_capabilities  | Schema_name    | Credential_data          |
       | --revocation --public-did                |                   | driverslicense | Data_DL_NormalizedValues |
       | --revocation --public-did --did-exchange | --did-exchange    | driverslicense | Data_DL_NormalizedValues |
       | --revocation --public-did --multitenant  | --multitenant     | driverslicense | Data_DL_NormalizedValues |

  @T004.1-RFC0453
  Scenario Outline: Issue a credential with revocation, with the Issuer beginning with an offer, and then revoking the credential
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Bob" has an issued <Schema_name> credential <Credential_data> from "Acme"
    Then "Acme" revokes the credential
    And "Bob" has the credential issued

    Examples:
       | Acme_capabilities                        | Bob_capabilities  | Schema_name    | Credential_data          |
       | --revocation --public-did --mediation    | --mediation       | driverslicense | Data_DL_NormalizedValues |
