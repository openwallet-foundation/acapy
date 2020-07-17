These are the ACA-py steps and APIs involved to support credential revocation.

0.  Publish credential definition 
    ```
    POST /credential-definitions
    {
      "schema_id": schema_id,
      "support_revocation": true
    }
    Response:
    {
      "credential_definition_id": "credential_definition_id"
    }
    ```

0. Create (but not publish yet) Revocation registry
    ```
    POST /revocation/create-registry,    
    {
        "credential_definition_id": "credential_definition_id",
        "max_cred_num": size_of_revocation_registry
    }
    Response:
    {
      "revoc_reg_id": "revocation_registry_id",
      "tails_hash": hash_of_tails_file,
      "cred_def_id": "credential_definition_id",
      ...
    }
   ```

0.  Get the tail file from agent
    ```
    Get /revocation/registry/{revocation_registry_id}/tails-file
    
    Response: stream down a binary file:
    content-type: application/octet-stream
    ...
    ```
0. Upload the tails file to a publicly accessible location
0. Update the tails file public URI to agent
    ```
    PATCH /revocation/registry/{revocation_registry_id}
    {
      "tails_public_uri": <tails_file_public_uri>
    }
   ```
0. Publish the revocation registry and first entry to the ledger
   ```
   POST /revocation/registry/{revocation_registry_id}/publish
   ```

0. Issue credential
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
0. Revoking credential (cred_rev_id is revocation_id from /issue-credential​/records)
    ```
    POST /issue-credential/revoke
    ```

0. When asking for proof, specify the timespan when the credential is NOT revoked
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
 