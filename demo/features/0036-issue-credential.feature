Feature: RFC 0036 Aries agent issue credential

  @T003-AIP10-RFC0036 @AcceptanceTest @P1 @critical @Indy @RFC0036
  Scenario Outline: Issue a credential with the Issuer beginning with an offer
    Given we have "2" agents
      | name  | role    | capabilities        |
      | Acme  | issuer  | <Acme_capabilities> |
      | Bob   | holder  | <Bob_capabilities>  |
    And "Acme" and "Bob" have an existing connection
    And "Acme" is ready to issue a credential
    When "Acme" offers a credential
    And "Bob" requests the credential
    And "Acme" issues the credential
    And "Bob" acknowledges the credential issue
    Then "Bob" has the credential issued

    Examples:
       | Acme_capabilities                      | Bob_capabilities          |
       | --public-did                           |                           |
       | --public-did --did-exchange            | --did-exchange            |
       | --public-did --mediation               | --mediation               |
       | --public-did --multitenant             | --multitenant             |
       | --public-did --mediation --multitenant | --mediation --multitenant |
