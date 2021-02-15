Feature: RFC 0036 Aries agent issue credential

  Background: create a schema and credential definition in order to issue a credential
    Given "Acme" has a public did
    And "Acme" is ready to issue a credential

  @T001-AIP10-RFC0036 @AcceptanceTest @P1 @critical @Indy @RFC0036
  Scenario: Issue a credential with the Holder beginning with a proposal
    Given "2" agents
      | name  | role   |
      | Acme  | issuer |
      | Bob   | holder |
    And "Acme" and "Bob" have an existing connection
    When "Bob" proposes a credential to "Acme"
    And "Acme" offers a credential
    And "Bob" requests the credential
    And "Acme" issues the credential
    And "Bob" acknowledges the credential issue
    Then "Bob" has the credential issued
