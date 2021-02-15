Feature: Application can validate a transaction based on specific
   tags associated in the account profile
   
   @fraudulent                   
   Scenario: Fraudulent tagged account trades an asset
      Given an account with "2400" asset points
      But the account profile is tagged as "fraudulent"
      When the account owner trades his asset
      Then the application should prompt an "XXXX" error
 