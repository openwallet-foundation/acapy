Feature: RFC 0454 Aries agent present proof

   @T001-RFC0454
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @PR @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
      
      @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --did-exchange            | --did-exchange            | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
      
      @Release @WalletType_Askar_AnonCreds @cred_type_vc_di
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --wallet-type askar-anoncreds --cred-type vc_di | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
      
      @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --wallet-type askar-anoncreds |                               | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did                           | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T001-RFC0454-DID-PEER
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "2" agents
         | name  | role     | capabilities        | extra        |
         | Faber | verifier | <Acme_capabilities> | <Acme_extra> |
         | Bob   | prover   | <Bob_capabilities>  | <Bob_extra>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @PR @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                      | Acme_extra        | Bob_capabilities   | Bob_extra         | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --did-exchange --emit-did-peer-2            | | --did-exchange --emit-did-peer-2     | | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                          | Acme_extra        | Bob_capabilities              | Bob_extra         | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --wallet-type askar-anoncreds --emit-did-peer-2 | | --wallet-type askar-anoncreds --emit-did-peer-2 | | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T001.1-RFC0454
   Scenario Outline: Present Proof where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did                           |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --public-did --mediation --multitenant | --mediation --multitenant | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                      | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --public-did --mediation --multitenant --wallet-type askar-anoncreds | --mediation --multitenant --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T001.2-RFC0454
   Scenario Outline: Present Proof json-ld where the prover does not propose a presentation of the proof and is acknowledged
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued json-ld <Schema_name> credential <Credential_data> from "<issuer>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for json-ld proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @PR @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                                         | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --public-did --cred-type json-ld                          |                           | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                                         | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --cred-type json-ld --did-exchange           | --did-exchange            | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                                         | Bob_capabilities          | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --public-did --cred-type json-ld --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T002-RFC0454
   Scenario Outline: Present Proof where the issuer revokes the credential and the proof fails
      Given we have "2" agents
         | name  | role     | capabilities        |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "<issuer>" revokes the credential
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      @PR @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @Release @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did --did-exchange   | --did-exchange   | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @Release @WalletType_Askar_AnonCreds @cred_type_vc_di
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did --wallet-type askar-anoncreds --cred-type vc_di | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |


   @T002.1-RFC0454
   Scenario Outline: Present Proof where the issuer revokes the credential and the proof fails
      Given we have "3" agents
         | name  | role     | capabilities        |
         | Acme  | issuer   | <Acme_capabilities> |
         | Faber | verifier | <Acme_capabilities> |
         | Bob   | prover   | <Bob_capabilities>  |
      And "<issuer>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name> credential <Credential_data> from "<issuer>"
      And "<issuer>" revokes the credential
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      @WalletType_Askar
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Acme   | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Faber  | --revocation --public-did                  |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --mediation      |                  | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --multitenant    | --multitenant    | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @WalletType_Askar_AnonCreds
      Examples:
         | issuer | Acme_capabilities                          | Bob_capabilities | Schema_name       | Credential_data   | Proof_request     |
         | Faber  | --revocation --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --mediation --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |
         | Acme   | --revocation --public-did --multitenant --wallet-type askar-anoncreds | --multitenant --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T003-RFC0454.1
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, neither credential is revoked
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @PR @Release @WalletType_Askar
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |

      @Release @WalletType_Askar_AnonCreds @cred_type_vc_di
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds --cred-type vc_di | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |

   @T003-RFC0454.1f
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, neither credential is revoked, fails due to requesting request-level revocation
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      @PR @Release @WalletType_Askar
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_r2 |

      @TODO @WalletType_Askar_AnonCreds
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_r2 |

   @T003-RFC0454.2
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, and the revocable credential is revoked, and the proof checks for revocation and fails
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer1>" revokes the credential
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verification fail

      @PR @Release @WalletType_Askar
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_r2 |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                    |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id |

   @T003-RFC0454.3
   Scenario Outline: Present Proof for multiple credentials where the one is revocable and one isn't, and the revocable credential is revoked, and the proof doesn't check for revocation and passes
      Given we have "4" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Acme2 | issuer2  | <Acme2_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer1>" revokes the credential
      And "<issuer2>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_2> credential <Credential_data_2> from "<issuer2>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request with explicit revocation status for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @PR @Release @WalletType_Askar
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                             |
         | Acme1   | --revocation --public-did | Acme2   | --public-did       |         | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_no_revoc |

      @PR @Release @WalletType_Askar_AnonCreds
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                             |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_no_revoc |

      @PR @Release @WalletType_Askar_AnonCreds @cred_type_vc_di
      Examples:
         | issuer1 | Acme1_capabilities        | issuer2 | Acme2_capabilities | Bob_cap | Schema_name_1     | Credential_data_1 | Schema_name_2 | Credential_data_2 | Proof_request                             |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds --cred-type vc_di | Acme2   | --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | health_id     | Data_DL_MaxValues | DL_age_over_19_v2_with_health_id_no_revoc |

   @T003-RFC0454.4
   Scenario Outline: Present Proof for a credential where multiple credentials are issued and all but one are revoked
      Given we have "3" agents
         | name  | role     | capabilities         |
         | Acme1 | issuer1  | <Acme1_capabilities> |
         | Faber | verifier | <Acme1_capabilities> |
         | Bob   | prover   | <Bob_cap>   |
      And "<issuer1>" and "Bob" have an existing connection
      And "Bob" has an issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "<issuer1>" revokes the credential
      And "Bob" has another issued <Schema_name_1> credential <Credential_data_1> from "<issuer1>"
      And "Faber" and "Bob" have an existing connection
      When "Faber" sends a request with explicit revocation status for proof presentation <Proof_request> to "Bob"
      Then "Faber" has the proof verified

      @WalletType_Askar
      Examples:
         | issuer1 | Acme1_capabilities        | Bob_cap | Schema_name_1     | Credential_data_1 | Proof_request     |
         | Acme1   | --revocation --public-did |         | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @WalletType_Askar_AnonCreds
      Examples:
         | issuer1 | Acme1_capabilities                                      | Bob_cap                       | Schema_name_1     | Credential_data_1 | Proof_request     |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

      @WalletType_Askar_AnonCreds @cred_type_vc_di
      Examples:
         | issuer1 | Acme1_capabilities                                      | Bob_cap                       | Schema_name_1     | Credential_data_1 | Proof_request     |
         | Acme1   | --revocation --public-did --wallet-type askar-anoncreds --cred-type vc_di | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues | DL_age_over_19_v2 |

   @T003-RFC0454.5
   Scenario Outline: Present Proof for a vc_di-issued credential using "legacy" indy proof and the proof validates
      Given we have "2" agents
         | name  | role    | capabilities        | extra        |
         | Acme  | issuer  | <Acme_capabilities> | <Acme_extra> |
         | Bob   | holder  | <Bob_capabilities>  | <Bob_extra>  |
      And "Acme" and "Bob" have an existing connection
      And "Acme" is ready to issue a credential for <Schema_name>
      When "Acme" offers a credential with data <Credential_data>
      When "Bob" has the credential issued
      When "Acme" sets the credential type to <New_Cred_Type>
      When "Acme" sends a request with explicit revocation status for proof presentation <Proof_request> to "Bob"
      Then "Acme" has the proof verified

   @WalletType_Askar_AnonCreds @SwitchCredTypeTest @cred_type_vc_di
   Examples:
       | Acme_capabilities                                                         | Bob_capabilities              | Schema_name       | Credential_data   | Acme_extra | Bob_extra | New_Cred_Type | Proof_request     |
       | --public-did --wallet-type askar-anoncreds --cred-type vc_di --revocation | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues |            |           | indy          | DL_age_over_19_v2 |

   @T003-RFC0454.6
   Scenario Outline: Present Proof for a vc_di-issued credential using "legacy" indy proof and credential is revoked and the proof fails
      Given we have "2" agents
         | name  | role    | capabilities        | extra        |
         | Acme  | issuer  | <Acme_capabilities> | <Acme_extra> |
         | Bob   | holder  | <Bob_capabilities>  | <Bob_extra>  |
      And "Acme" and "Bob" have an existing connection
      And "Acme" is ready to issue a credential for <Schema_name>
      When "Acme" offers a credential with data <Credential_data>
      When "Bob" has the credential issued
      When "Acme" sets the credential type to <New_Cred_Type>
      And "Acme" revokes the credential
      When "Acme" sends a request for proof presentation <Proof_request> to "Bob"
      Then "Acme" has the proof verification fail

   @WalletType_Askar_AnonCreds @SwitchCredTypeTest @cred_type_vc_di
   Examples:
       | Acme_capabilities                                                         | Bob_capabilities              | Schema_name       | Credential_data   | Acme_extra | Bob_extra | New_Cred_Type | Proof_request     |
       | --public-did --wallet-type askar-anoncreds --cred-type vc_di --revocation | --wallet-type askar-anoncreds | driverslicense_v2 | Data_DL_MaxValues |            |           | indy          | DL_age_over_19_v2 |
