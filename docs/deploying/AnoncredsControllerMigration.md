# AnonCreds Controller Migration

To upgrade an agent to use AnonCreds a controller should implement the required changes to endpoints and payloads in a way that is backwards compatible. The controller can then trigger the upgrade via the upgrade endpoint.

## Step 1 - Endpoint Payload and Response Changes

There is endpoint and payload changes involved with creating **schema, credential definition and revocation objects**. Your controller will need to implement these changes for any endpoints it uses.

A good way to implement this with backwards compatibility is to get the wallet type via **/settings** and handle the existing endpoints when **wallet.type** is **askar** and the new anoncreds endpoints when **wallet.type** is **askar-anoncreds**. In this way the controller will handle both types of wallets in case the upgrade fails. After the upgrade is successful and stable the controller can be updated to only handle the new anoncreds endpoints.

## Schemas

### Creating a Schema:

- Change endpoint from **POST /schemas** to **POST /anoncreds/schema**
- Change payload and parameters from

```yml
params
 - conn_id
 - create_transaction_for_endorser
```

```json
{
  "attributes": ["score"],
  "schema_name": "simple",
  "schema_version": "1.0"
}
```

to

```json
{
  "options": {
    "create_transaction_for_endorser": false,
    "endorser_connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "schema": {
    "attrNames": ["score"],
    "issuerId": "WgWxqztrNooG92RXvxSTWv",
    "name": "Example schema",
    "version": "1.0"
  }
}
```

- options are not required
- **_issuerId_** is the public did to be used on the ledger
- The payload responses have changed

**_Responses_**

Without endorsement:

```json
{
  "sent": {
    "schema_id": "PzmGpSeCznzfPmv9B1EBqa:2:simple:1.0",
    "schema": {
      "ver": "1.0",
      "id": "PzmGpSeCznzfPmv9B1EBqa:2:simple:1.0",
      "name": "simple",
      "version": "1.0",
      "attrNames": ["score"],
      "seqNo": 541
    }
  },
  "schema_id": "PzmGpSeCznzfPmv9B1EBqa:2:simple:1.0",
  "schema": {
    "ver": "1.0",
    "id": "PzmGpSeCznzfPmv9B1EBqa:2:simple:1.0",
    "name": "simple",
    "version": "1.0",
    "attrNames": ["score"],
    "seqNo": 541
  }
}
```

to

```json
{
  "job_id": "string",
  "registration_metadata": {},
  "schema_metadata": {},
  "schema_state": {
    "schema": {
      "attrNames": ["score"],
      "issuerId": "WgWxqztrNooG92RXvxSTWv",
      "name": "Example schema",
      "version": "1.0"
    },
    "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "state": "finished"
  }
}
```

With endorsement:

```json
{
  "sent": {
    "schema": {
      "attrNames": [
        "score"
      ],
      "id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
      "name": "schema_name",
      "seqNo": 10,
      "ver": "1.0",
      "version": "1.0"
    },
    "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0"
  },
  "txn": {...}
}
```

to

```json
{
  "job_id": "12cb896d648242c8b9b0fff3b870ed00",
  "schema_state": {
    "state": "wait",
    "schema_id": "RbyPM1EP8fKCrf28YsC1qK:2:simple:1.1",
    "schema": {
      "issuerId": "RbyPM1EP8fKCrf28YsC1qK",
      "attrNames": [
        "score"
      ],
      "name": "simple",
      "version": "1.1"
    }
  },
  "registration_metadata": {
    "txn": {...}
  },
  "schema_metadata": {}
}
```

#### Getting schemas

- Change endpoint from **GET /schemas/created** to **GET /anoncreds/schemas**
- Response payloads have no change

#### Getting a schema

- Change endpoint from **GET /schemas/{schema_id}** to **GET /anoncreds/schema/{schema_id}**
- Response payload changed from

```json
{
  "schema": {
    "attrNames": ["score"],
    "id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "name": "schema_name",
    "seqNo": 10,
    "ver": "1.0",
    "version": "1.0"
  }
}
```

to

```json
{
  "resolution_metadata": {},
  "schema": {
    "attrNames": ["score"],
    "issuerId": "WgWxqztrNooG92RXvxSTWv",
    "name": "Example schema",
    "version": "1.0"
  },
  "schema_id": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
  "schema_metadata": {}
}
```

## Credential Definitions

### Creating a credential definition

- Change endpoint from **POST /credential-definitions** to **POST /anoncreds/credential-definition**
- Change payload and parameters from

```yml
params
 - conn_id
 - create_transaction_for_endorser
```

```json
{
  "revocation_registry_size": 1000,
  "schema_id": "WgWxqztrNooG92RXvxSTWv:2:simple:1.0",
  "support_revocation": true,
  "tag": "default"
}
```

to

```json
{
  "credential_definition": {
    "issuerId": "WgWxqztrNooG92RXvxSTWv",
    "schemaId": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "tag": "default"
  },
  "options": {
    "create_transaction_for_endorser": false,
    "endorser_connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "revocation_registry_size": 1000,
    "support_revocation": true
  }
}
```

- options are not required, revocation will default to false
- _**issuerId**_ is the public did to be used on the ledger
- _**schemaId**_ is the schema id on the ledger
- The payload responses have changed

**_Responses_**

Without Endoresment:

```json
{
  "sent": {
    "credential_definition_id": "CZGamdZoKhxiifjbdx3GHH:3:CL:558:default"
  },
  "credential_definition_id": "CZGamdZoKhxiifjbdx3GHH:3:CL:558:default"
}
```

to

```json
{
  "schema_state": {
    "state": "finished",
    "schema_id": "BpGaCdTwgEKoYWm6oPbnnj:2:simple:1.0",
    "schema": {
      "issuerId": "BpGaCdTwgEKoYWm6oPbnnj",
      "attrNames": ["score"],
      "name": "simple",
      "version": "1.0"
    }
  },
  "registration_metadata": {},
  "schema_metadata": {
    "seqNo": 555
  }
}
```

With Endorsement:

```json
{
  "sent": {
    "credential_definition_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
  },
  "txn": {...}
}
```

```json
{
  "job_id": "7082e58aa71d4817bb32c3778596b012",
  "credential_definition_state": {
    "state": "wait",
    "credential_definition_id": "RbyPM1EP8fKCrf28YsC1qK:3:CL:547:default",
    "credential_definition": {
      "issuerId": "RbyPM1EP8fKCrf28YsC1qK",
      "schemaId": "RbyPM1EP8fKCrf28YsC1qK:2:simple:1.1",
      "type": "CL",
      "tag": "default",
      "value": {
        "primary": {...},
        "revocation": {...}
      }
    }
  },
  "registration_metadata": {
    "txn": {...}
  },
  "credential_definition_metadata": {}
}
```

### Getting credential definitions

- Change endpoint from **GET /credential-definitions/created** to **GET /anoncreds/credential-definitions**
- Response payloads have no change

### Getting a credential definition

- Change endpoint from **GET /credential-definitions/{schema_id}** to **GET /anoncreds/credential-definition/{cred_def_id}**
- Response payload changed from

```json
{
  "credential_definition": {
    "id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag",
    "schemaId": "20",
    "tag": "tag",
    "type": "CL",
    "value": {...},
      "revocation": {...}
    },
    "ver": "1.0"
  }
}
```

to

```json
{
  "credential_definition": {
    "issuerId": "WgWxqztrNooG92RXvxSTWv",
    "schemaId": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "tag": "default",
    "type": "CL",
    "value": {...},
      "revocation": {...}
    }
  },
  "credential_definition_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag",
  "credential_definitions_metadata": {},
  "resolution_metadata": {}
}
```

## Revocation

Most of the changes with revocation endpoints only require prepending `/anoncreds` to the path. There are some other subtle changes listed below.

### Create and publish registry definition

- The endpoints **POST /revocation/create-registry** and **POST /revocation/registry/{rev_reg_id}/definition** have been replaced by the single endpoint **POST /anoncreds/revocation-registry-definition**
- Instead of creating the registry with **POST /revocation/create-registry** and payload

```json
{
  "credential_definition_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag",
  "max_cred_num": 1000
}
```

- And then publishing with **POST /revocation/registry/{rev_reg_id}/definition**

```yml
params
 - conn_id
 - create_transaction_for_endorser
```

- Use **POST /anoncreds/revocation-registry-definition** with payload

```json
{
  "options": {
    "create_transaction_for_endorser": false,
    "endorser_connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "revocation_registry_definition": {
    "credDefId": "WgWxqztrNooG92RXvxSTWv:2:schema_name:1.0",
    "issuerId": "WgWxqztrNooG92RXvxSTWv",
    "maxCredNum": 777,
    "tag": "default"
  }
}
```

- options are not required, revocation will default to false
- _**issuerId**_ is the public did to be used on the ledger
- _**credDefId**_ is the cred def id on the ledger
- The payload responses have changed

**_Responses_**

Without endorsement:

```json
{
  "sent": {
    "revocation_registry_id": "CZGamdZoKhxiifjbdx3GHH:4:CL:558:default"
  },
  "revocation_registry_id": "CZGamdZoKhxiifjbdx3GHH:4:CL:558:default"
}
```

to

```json
{
  "revocation_registry_definition_state": {
    "state": "finished",
    "revocation_registry_definition_id": "BpGaCdTwgEKoYWm6oPbnnj:4:BpGaCdTwgEKoYWm6oPbnnj:3:CL:555:default:CL_ACCUM:default",
    "revocation_registry_definition": {
      "issuerId": "BpGaCdTwgEKoYWm6oPbnnj",
      "revocDefType": "CL_ACCUM",
      "credDefId": "BpGaCdTwgEKoYWm6oPbnnj:3:CL:555:default",
      "tag": "default",
      "value": {...}
    }
  },
  "registration_metadata": {},
  "revocation_registry_definition_metadata": {
    "seqNo": 569
  }
}
```

With endorsement:

```json
{
  "sent": {
    "result": {
      "created_at": "2021-12-31T23:59:59Z",
      "cred_def_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag",
      "error_msg": "Revocation registry undefined",
      "issuer_did": "WgWxqztrNooG92RXvxSTWv",
      "max_cred_num": 1000,
      "pending_pub": [
        "23"
      ],
      "record_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "revoc_def_type": "CL_ACCUM",
      "revoc_reg_def": {
        "credDefId": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag",
        "id": "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
        "revocDefType": "CL_ACCUM",
        "tag": "string",
        "value": {...},
        "ver": "1.0"
      },
      "revoc_reg_entry": {...},
      "revoc_reg_id": "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0",
      "state": "active",
      "tag": "string",
      "tails_hash": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
      "tails_local_path": "string",
      "tails_public_uri": "string",
      "updated_at": "2021-12-31T23:59:59Z"
    }
  },
  "txn": {...}
}
```

to

```json
{
  "job_id": "25dac53a1fb84cb8a5bf1b4362fbca11",
  "revocation_registry_definition_state": {
    "state": "wait",
    "revocation_registry_definition_id": "RbyPM1EP8fKCrf28YsC1qK:4:RbyPM1EP8fKCrf28YsC1qK:3:CL:547:default:CL_ACCUM:default",
    "revocation_registry_definition": {
      "issuerId": "RbyPM1EP8fKCrf28YsC1qK",
      "revocDefType": "CL_ACCUM",
      "credDefId": "RbyPM1EP8fKCrf28YsC1qK:3:CL:547:default",
      "tag": "default",
      "value": {...}
    }
  },
  "registration_metadata": {
    "txn": {...}
  },
  "revocation_registry_definition_metadata": {}
}
```

### Send revocation entry or list to ledger

- Changes from **POST /revocation/registry/{rev_reg_id}/entry** to **POST /anoncreds/revocation-list**
- Change from

```yml
params
 - conn_id
 - create_transaction_for_endorser
```

to

```json
{
  "options": {
    "create_transaction_for_endorser": false,
    "endorser_connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "rev_reg_def_id": "WgWxqztrNooG92RXvxSTWv:4:WgWxqztrNooG92RXvxSTWv:3:CL:20:tag:CL_ACCUM:0"
}
```

- options are not required
- _**rev_reg_def_id**_ is the revocation registry definition id on the ledger
- The payload responses have changed

**_Responses_**

Without endorsement:

```json
{
  "sent": {
    "revocation_registry_id": "BpGaCdTwgEKoYWm6oPbnnj:4:BpGaCdTwgEKoYWm6oPbnnj:3:CL:555:default:CL_ACCUM:default"
  },
  "revocation_registry_id": "BpGaCdTwgEKoYWm6oPbnnj:4:BpGaCdTwgEKoYWm6oPbnnj:3:CL:555:default:CL_ACCUM:default"
}
```

to

```json

```

### Get current active registry:

- Change from **GET /revocation/active-registry/{cred_def_id}** to **GET /anoncreds/revocation/active-registry/{cred_def_id}**
- No payload changes

### Rotate active registry

- Change from **POST /revocation/active-registry/{cred_def_id}/rotate** to **POST /anoncreds/revocation/active-registry/{cred_def_id}/rotate**
- No payload changes

### Get credential revocation status

- Change from **GET /revocation/credential-record** to **GET /anoncreds/revocation/credential-record**
- No payload changes

### Publish revocations

- Change from **POST /revocation/publish-revocations** to **POST /anoncreds/revocation/publish-revocations**
- Change payload and parameters from

```yml
params
 - conn_id
 - create_transaction_for_endorser
```

```json
{
  "rrid2crid": {
    "additionalProp1": ["12345"],
    "additionalProp2": ["12345"],
    "additionalProp3": ["12345"]
  }
}
```

to

```json
{
  "options": {
    "create_transaction_for_endorser": false,
    "endorser_connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
  },
  "rrid2crid": {
    "additionalProp1": ["12345"],
    "additionalProp2": ["12345"],
    "additionalProp3": ["12345"]
  }
}
```

- options are not required

### Get registries

- Change from **GET /revocation/registries/created** to **GET /anoncreds/revocation/registries**
- No payload changes

### Get registry

- Changes from **GET /revocation/registry/{rev_reg_id}** to **GET /anoncreds/revocation/registry/{rev_reg_id}**
- No payload changes

### Fix reocation state

- Changes from **POST /revocation/registry/{rev_reg_id}/fix-revocation-entry-state** to **POST /anoncreds/revocation/registry/{rev_reg_id}/fix-revocation-state**
- No payload changes

### Get number of issued credentials

- Changes from **GET /revocation/registry/{rev_reg_id}/issued** to **GET /anoncreds/revocation/registry/{rev_reg_id}/issued**
- No payload changes

### Get credential details

- Changes from **GET /revocation/registry/{rev_reg_id}/issued/details** to **GET /anoncreds/revocation/registry/{rev_reg_id}/issued/details**
- No payload changes

### Get revoked credential details

- Changes from **GET /revocation/registry/{rev_reg_id}/issued/indy_recs** to **GET /anoncreds/revocation/registry/{rev_reg_id}/issued/indy_recs**
- No payload changes

### Set state manually

- Changes from **PATCH /revocation/registry/{rev_reg_id}/set-state** to **PATCH /anoncreds/revocation/registry/{rev_reg_id}/set-state**
- No payload changes

### Upload tails file

- Changes from **PUT /revocation/registry/{rev_reg_id}/tails-file** to **PUT /anoncreds/registry/{rev_reg_id}/tails-file**
- No payload changes

### Download tails file

- Changes from **GET /revocation/registry/{rev_reg_id}/tails-file** to **GET /anoncreds/revocation/registry/{rev_reg_id}/tails-file**
- No payload changes

### Revoke a credential

- Changes from **POST /revocation/revoke** to **POST /anoncreds/revocation/revoke**
- Change payload and parameters from

### Clear pending revocations

- **POST /revocation/clear-pending-revocations** has been removed.

### Delete tails file

- Endpoint **DELETE /revocation/delete-tails-server** has been removed

### Update tails file

- Endpoint **PATCH /revocation/registry/{rev_reg_id}** has been removed

### Additional Endpoints

- **PUT /anoncreds/registry/{rev_reg_id}/active** is available to set the active registry

## Step 2 - Trigger the upgrade via the upgrade endpoint

The upgrade endpoint is at **POST /anoncreds/wallet/upgrade**.

You need to be careful doing this, as there is no way to downgrade the wallet. It is recommended highly recommended to back-up any wallets and to test the upgrade in a development environment before upgrading a production wallet.

Params: `wallet_name` is the name of the wallet to upgrade. Used to prevent accidental upgrades.

The behavior for a base wallet (standalone) or admin wallet in multitenant mode is slightly different from the behavior of a subwallet (or tenant) in multitenancy mode. However, the upgrade process is the same.

1. Backup the wallet
2. Scale down any controller instances on old endpoints
3. Call the upgrade endpoint
4. Scale up the controller instances to handle new endpoints

### Base wallet (standalone) or admin wallet in multitenant mode

The agent will get a 503 error during the upgrade process. Any agent instance will shut down when the upgrade is complete. It is up to the aca-py agent to start up again. After the upgrade is complete the old endpoints will no longer be available and result in a 400 error.

The aca-py agent will work after the restart. However, it will receive a warning for having the wrong wallet type configured. It is recommended to change the `wallet-type` to `askar-anoncreds` in the agent configuration file or start-up command.

### Subwallet (tenant) in multitenancy mode

The sub-tenant which is in the process of being upgraded will get a 503 error during the upgrade process. All other sub-tenants will continue to operate normally. After the upgrade is complete the sub-tenant will be able to use the new endpoints. The old endpoints will no longer be available and result in a 403 error. Any aca-py agents will remain running after the upgrade and it's not required that the aca-py agent restarts. 
