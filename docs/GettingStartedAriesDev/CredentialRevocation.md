These are the ACA-py steps and APIs involved to support credential revocation.

Run ACA-Py with tails server support enabled. You will need to have the URL of an running instance of https://github.com/bcgov/indy-tails-server.

Incude the command line parameter `--tails-server-base-url <indy-tails-server url>`

0.  Publish credential definition

    Credential definition is created. All required revocation collateral is also created
    and managed including revocation registry definition, entry, and tails file.

    ```
    POST /credential-definitions
    {
      "schema_id": schema_id,
      "support_revocation": true,
      # Only needed if support_revocation is true. Defaults to 100
      "revocation_registry_size": size_int,
      "tag": cred_def_tag # Optional

    }
    Response:
    {
      "credential_definition_id": "credential_definition_id"
    }
    ```

1.  Issue credential

    This endpoint manages revocation data. If new revocation registry data is required,
    it is automatically managed in the background.

    ```
    POST /issue-credential/send-offer
    {
        "cred_def_id": credential_definition_id,
        "revoc_reg_id": revocation_registry_id
        "auto_remove": False, # We need the credential exchange record when revoking
        ...
    }
    Response
    {
        "credential_exchange_id": credential_exchange_id
    }
    ```

2.  Revoking credential

    ```
    POST /issue-credential/revoke?rev_reg_id=<revocation_registry_id>
         &cred_rev_id=<credential_revocation_id>&publish=<true|false>
    ```

    If publish=false, you must use `​/issue-credential​/publish-revocations` to publish
    pending revocations in batches. Revocation are not written to ledger until this is called.

3.  When asking for proof, specify the timespan when the credential is NOT revoked
    ```
     POST /present-proof/send-request
     {
       "connection_id": ...,
       "proof_request": {
         "requested_attributes": [
           {
             "name": ...
             "restrictions": ...,
             ...
             "non_revoked": # Optional, override the global one when specified
             {
               "from": <seconds from Unix Epoch> # Optional, default is 0
               "to": <seconds from Unix Epoch>
             }
           },
           ...
         ],
         "requested_predicates": [
           {
             "name": ...
             ...
             "non_revoked": # Optional, override the global one when specified
             {
               "from": <seconds from Unix Epoch> # Optional, default is 0
               "to": <seconds from Unix Epoch>
             }
           },
           ...
         ],
         "non_revoked": # Optional, only check revocation if specified
         {
           "from": <seconds from Unix Epoch> # Optional, default is 0
           "to": <seconds from Unix Epoch>
         }
       }
     }
    ```
