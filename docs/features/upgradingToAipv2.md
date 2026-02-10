# Upgrading Your Controller to AIP 2.0

This guide helps you upgrade your controller application to use AIP 2.0 endpoints and features when working with ACA-Py.

## Overview

AIP 2.0 introduces significant changes to how credential and presentation exchanges are handled. AIP 1.0 exclusively supported Indy credentials. AIP 2.0 supports multiple credential formats, providing better interoperability and flexibility.

**Key differences from AIP 1.0:**
- New REST endpoints under `/issue-credential-2.0` and `/present-proof-2.0` namespaces
- Format-specific filters in request bodies
- New exchange record types with updated field names
- Updated webhook topics and payload structures
- Enhanced state management

**Credential format options:**
- **`anoncreds` filter** (Recommended): Requires upgraded wallet type (`askar-anoncreds`). This is the recommended option offering improved performance, better features, and future-proof compatibility.
- **`indy` filter**: Backward compatible with AIP 1.0, works with existing Indy wallets (no wallet upgrade required)

> **💡 Recommendation:** While the `indy` filter provides backward compatibility, we strongly recommend upgrading to `askar-anoncreds` wallet and using the `anoncreds` filter. The AnonCreds format offers better performance, improved features, and is the future direction for credential formats. See the [AnonCreds Filter](#anoncreds-filter-requires-wallet-upgrade) section for upgrade instructions.

## Prerequisites

- ACA-Py instance with AIP 2.0 support (typically ACA-Py 0.7.0 or later)
- Controller application using ACA-Py's Admin API
- Understanding of Aries protocols and REST APIs
- For `anoncreds` filter: ACA-Py started with `--wallet-type askar-anoncreds` (in multitenant mode, this setting can be overwritten per tenant)
- For existing wallets with the `askar` type, there's an endpoint to upgrade the wallet to `askar-anoncreds`

## API Endpoints

When upgrading your controller, update all API calls to use the new v2.0 endpoints. The v2.0 endpoints replace the v1.0 endpoints and provide enhanced functionality.

### Credential Exchange Endpoints

- `GET /issue-credential-2.0/records` - List exchanges (query params: `connection_id`, `role`, `state`, `thread_id`, `limit`, `offset`, `order_by`, `descending`)
- `GET /issue-credential-2.0/records/{cred_ex_id}` - Get single exchange
- `POST /issue-credential-2.0/create` - Create offer (requires `filter` in body)
- `POST /issue-credential-2.0/send-offer` - Send offer (requires `connection_id` and `filter`)
- `POST /issue-credential-2.0/records/{cred_ex_id}/send-request` - Send request
- `POST /issue-credential-2.0/records/{cred_ex_id}/issue` - Issue credential
- `POST /issue-credential-2.0/records/{cred_ex_id}/store` - Store credential
- `DELETE /issue-credential-2.0/records/{cred_ex_id}` - Remove exchange

### Presentation Exchange Endpoints

- `GET /present-proof-2.0/records` - List exchanges (query params: `connection_id`, `role`, `state`, `thread_id`, `limit`, `offset`)
- `GET /present-proof-2.0/records/{pres_ex_id}` - Get single exchange
- `GET /present-proof-2.0/records/{pres_ex_id}/credentials` - List available credentials
- `POST /present-proof-2.0/send-proposal` - Send proposal
- `POST /present-proof-2.0/create-request` - Create request (requires `presentation_request` in body)
- `POST /present-proof-2.0/send-request` - Send request
- `POST /present-proof-2.0/records/{pres_ex_id}/send-presentation` - Send presentation
- `POST /present-proof-2.0/records/{pres_ex_id}/verify-presentation` - Verify presentation
- `DELETE /present-proof-2.0/records/{pres_ex_id}` - Remove exchange

## Exchange Records

AIP 2.0 introduces new exchange record types that replace the v1.0 records. Understanding these record structures is essential for properly handling exchanges in your controller.

### Credential Exchange Records (V20CredExRecord)

Key fields:
- `cred_ex_id`: Unique identifier for the exchange (replaces `credential_exchange_id`)
- `connection_id`: Connection identifier
- `thread_id`: Thread identifier for message threading
- `state`: Current state of the exchange
- `role`: Role in the exchange (`issuer` or `holder`)
- `initiator`: Who initiated the exchange (`self` or `external`)
- `credential_definition_id`: Credential definition identifier
- `schema_id`: Schema identifier
- `credential_id`: Stored credential identifier (after issuance)
- `auto_offer`: Whether to automatically send offers
- `auto_issue`: Whether to automatically issue credentials
- `auto_remove`: Whether to automatically remove the record on completion
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

**Exchange States:**
- `proposal-sent`: Proposal has been sent
- `proposal-received`: Proposal has been received
- `offer-sent`: Offer has been sent
- `offer-received`: Offer has been received
- `request-sent`: Request has been sent
- `request-received`: Request has been received
- `credential-issued`: Credential has been issued
- `credential-received`: Credential has been received
- `done`: Exchange completed successfully
- `abandoned`: Exchange was abandoned

### Presentation Exchange Records (V20PresExRecord)

Key fields:
- `pres_ex_id`: Unique identifier for the exchange (replaces `presentation_exchange_id`)
- `connection_id`: Connection identifier
- `thread_id`: Thread identifier for message threading
- `state`: Current state of the exchange
- `role`: Role in the exchange (`prover` or `verifier`)
- `initiator`: Who initiated the exchange (`self` or `external`)
- `auto_present`: Whether to automatically send presentations
- `auto_verify`: Whether to automatically verify presentations
- `verified`: Boolean indicating verification result (for verifier role, after verification)
- `verified_msgs`: Verification result messages
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

**Exchange States:**
- `proposal-sent`: Proposal has been sent
- `proposal-received`: Proposal has been received
- `request-sent`: Request has been sent
- `request-received`: Request has been received
- `presentation-sent`: Presentation has been sent
- `presentation-received`: Presentation has been received
- `done`: Exchange completed successfully
- `abandoned`: Exchange was abandoned

## Filters

AIP 2.0 uses format-specific filters in request bodies when creating credential offers and presentation requests. Unlike AIP 1.0, AIP 2.0 supports multiple credential formats, allowing your controller to specify filters for different credential types.

### Credential Exchange Filters

The `filter` field is required in requests to endpoints like:
- `POST /issue-credential-2.0/create`
- `POST /issue-credential-2.0/send-offer`
- `POST /issue-credential-2.0/send-request`

You must include at least one format filter (`indy` or `anoncreds`). You can include both formats to allow the holder to choose which format they prefer.

#### AnonCreds Filter (Requires Wallet Upgrade)

> **💡 Recommended:** The `anoncreds` filter uses the newer AnonCreds format, which offers improved performance, better features, and is the recommended approach for new deployments. If you haven't already upgraded your wallet, we encourage you to do so.

The `anoncreds` filter uses the newer AnonCreds format and requires upgrading your wallet to `askar-anoncreds`:

```json
{
  "filter": {
    "anoncreds": {
      "cred_def_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
    }
  }
}
```

**Important:** To use the `anoncreds` filter, start ACA-Py with `--wallet-type askar-anoncreds`:

```bash
aca-py start \
  --wallet-type askar-anoncreds \
  --wallet-name mywallet \
  --wallet-key mykey
```

**Multitenant mode:** In multitenant mode, the wallet type setting can be overwritten per tenant. Each tenant can have its own wallet type configuration.

**Upgrading existing wallets:** For existing wallets with the `askar` type, you can upgrade to `askar-anoncreds` using the wallet upgrade endpoint:

```
POST /anoncreds/wallet/upgrade?wallet_name=<wallet_name>
```

> **⚠️ Warning:** This upgrade is irreversible. You cannot downgrade from `askar-anoncreds` back to `askar`. It is highly recommended to back up your wallet and test the upgrade in a development environment before upgrading a production wallet.

**Benefits of upgrading to `askar-anoncreds`:**
- Improved performance and efficiency
- Better support for modern credential features
- Future-proof solution aligned with AnonCreds specifications
- Enhanced interoperability with other AnonCreds-compatible systems

**AnonCreds filter fields:**
- `cred_def_id` (string, optional): Credential definition identifier
- `schema_id` (string, optional): Schema identifier
- `schema_issuer_id` (string, optional): Schema issuer ID
- `schema_name` (string, optional): Schema name
- `schema_version` (string, optional): Schema version
- `issuer_id` (string, optional): Credential issuer ID

#### Indy Filter (Backward Compatible)

The `indy` filter provides backward compatibility with AIP 1.0 and works with existing Indy wallets. It has a similar structure to the `anoncreds` filter:

```json
{
  "filter": {
    "indy": {
      "cred_def_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
    }
  }
}
```

**Indy filter fields:**
- `cred_def_id` (string, optional): Credential definition identifier
- `schema_id` (string, optional): Schema identifier
- `schema_issuer_did` (string, optional): Schema issuer DID
- `schema_name` (string, optional): Schema name
- `schema_version` (string, optional): Schema version (e.g., "1.0")
- `issuer_did` (string, optional): Credential issuer DID

### Presentation Request Filters

When creating presentation requests, you specify a `presentation_request` object that supports multiple proof formats. The `presentation_request` field is used in endpoints like:
- `POST /present-proof-2.0/create-request`
- `POST /present-proof-2.0/send-request`

You must include at least one format (`indy` or `anoncreds`).

For detailed examples and advanced features of building presentation requests, see the [AnonCreds Specification - Create Presentation Request](https://anoncreds.github.io/anoncreds-spec/#create-presentation-request) section.

#### AnonCreds Proof Request

For AnonCreds proof requests:

```json
{
  "presentation_request": {
    "anoncreds": {
      "name": "Proof of Identity",
      "version": "1.0",
      "requested_attributes": {
        "attr1_referent": {
          "name": "name",
          "restrictions": [
            {
              "cred_def_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
            }
          ]
        }
      },
      "requested_predicates": {
        "pred1_referent": {
          "name": "age",
          "p_type": ">=",
          "p_value": 18,
          "restrictions": [
            {
              "cred_def_id": "WgWxqztrNooG92RXvxSTWv:3:CL:20:tag"
            }
          ]
        }
      },
      "non_revoked": {
        "from": 1234567890,
        "to": 1234567890
      }
    }
  }
}
```

#### Indy Proof Request

The `indy` proof request has a similar structure to the `anoncreds` proof request. Use `"indy"` instead of `"anoncreds"` in the `presentation_request` object for backward compatibility with AIP 1.0.

## Webhooks

When upgrading to AIP 2.0, your controller's webhook handler must be updated to process the new v2.0 webhook topics and payload structures. Configure webhooks using `--webhook-url` when starting ACA-Py:

```bash
aca-py start --webhook-url https://your-controller.example.com/webhooks
```

Webhooks are sent as POST requests to the configured URL with the topic appended as a path component.

### Credential Exchange Webhooks

**Topic:** `issue_credential_v2_0`

**Webhook URL:** `https://your-controller.example.com/webhooks/issue_credential_v2_0`

**Example payload:**
```json
{
  "connection_id": "conn-123",
  "cred_ex_id": "cred-ex-456",
  "thread_id": "thread-789",
  "state": "offer-sent",
  "role": "issuer",
  "initiator": "self",
  "credential_definition_id": "cred-def-id",
  "schema_id": "schema-id",
  "auto_offer": false,
  "auto_issue": false,
  "auto_remove": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:01Z"
}
```

**Key webhook fields:**
- `cred_ex_id`: The credential exchange identifier (use this to retrieve full details via API)
- `state`: Current state of the exchange
- `role`: Your role in the exchange (`issuer` or `holder`)
- `connection_id`: Connection identifier
- `thread_id`: Thread identifier for message correlation

### Presentation Exchange Webhooks

**Topic:** `present_proof_v2_0`

**Webhook URL:** `https://your-controller.example.com/webhooks/present_proof_v2_0`

**Example payload:**
```json
{
  "connection_id": "conn-123",
  "pres_ex_id": "pres-ex-456",
  "thread_id": "thread-789",
  "state": "request-received",
  "role": "prover",
  "initiator": "external",
  "auto_present": false,
  "auto_verify": false,
  "verified": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:01Z"
}
```

**Key webhook fields:**
- `pres_ex_id`: The presentation exchange identifier (use this to retrieve full details via API)
- `state`: Current state of the exchange
- `role`: Your role in the exchange (`prover` or `verifier`)
- `connection_id`: Connection identifier
- `thread_id`: Thread identifier for message correlation
- `verified`: Boolean indicating verification result (for verifier role, after verification)

### Webhook Processing Best Practices

1. **Idempotency**: Webhooks may be delivered multiple times. Implement idempotent handlers using the exchange ID and state.

2. **State Transitions**: Monitor state transitions to trigger appropriate actions:
   - `offer-received` → Retrieve offer details and decide whether to request
   - `request-received` → Issue credential
   - `credential-received` → Store credential
   - `request-received` (presentation) → Prepare and send presentation
   - `presentation-received` → Verify presentation

3. **Error Handling**: Check for `error_msg` field in webhook payloads to handle errors.

4. **Webhook Topics**: Ensure your webhook handler distinguishes between v1.0 and v2.0 topics:
   - v1.0: `issue_credential`, `present_proof`
   - v2.0: `issue_credential_v2_0`, `present_proof_v2_0`

## Migration Steps

This section provides a step-by-step guide for migrating your controller code from AIP 1.0 to AIP 2.0.

### 1. Update API Calls

Replace all v1.0 endpoint calls in your controller code with v2.0 equivalents:

**Before (v1.0):**
- `GET /issue-credential/records`
- `POST /issue-credential/send-offer`

**After (v2.0):**
- `GET /issue-credential-2.0/records`
- `POST /issue-credential-2.0/send-offer`

### 2. Update Webhook Handlers

Update your controller's webhook handlers to process v2.0 topics:

**Before (v1.0):**
- Webhook topic: `issue_credential`
- Field name: `credential_exchange_id`

**After (v2.0):**
- Webhook topic: `issue_credential_v2_0`
- Field name: `cred_ex_id` (note: field name changed)

**Key changes:**
- Update webhook route to handle `/webhooks/issue_credential_v2_0` path
- Use `cred_ex_id` instead of `credential_exchange_id` to access the exchange ID
- Handle state transitions: `offer-received`, `request-received`, `credential-received`

**Supporting both versions during migration:**
- Check the topic name to determine which field name to use
- Use `cred_ex_id` for v2.0 topics, `credential_exchange_id` for v1.0 topics

### 3. Update Filter Logic in Request Bodies

Since AIP 1.0 exclusively supported Indy credentials, you'll need to choose between using the `indy` filter (backward compatible) or `anoncreds` filter (requires wallet upgrade):

**Before (v1.0 - Credential Offer):**
- Use `credential_definition_id` field directly
- No filter object required

**After (v2.0 - Using indy filter, backward compatible):**
- Wrap credential definition ID in `filter.indy.cred_def_id`
- Use `@type: "issue-credential/2.0/credential-preview"` in credential preview

**After (v2.0 - Using anoncreds filter, requires askar-anoncreds wallet):**
- Wrap credential definition ID in `filter.anoncreds.cred_def_id`
- Requires `--wallet-type askar-anoncreds` when starting ACA-Py

**Before (v1.0 - Presentation Request):**
- Use `proof_request` object directly

**After (v2.0 - Presentation Request):**
- Use `presentation_request` object with format-specific request (`indy` or `anoncreds`)
- Wrap proof request structure in `presentation_request.indy` or `presentation_request.anoncreds`

### 4. Update Exchange Record Field Access

Update your controller code that accesses exchange record fields:

**Before (v1.0):**
- `credential_exchange_id` - Credential exchange identifier
- `credential_definition_id` - Credential definition identifier
- `presentation_exchange_id` - Presentation exchange identifier

**After (v2.0):**
- `cred_ex_id` - Credential exchange identifier (shorter name)
- `cred_def_id` - Credential definition identifier (shorter name)
- `pres_ex_id` - Presentation exchange identifier (shorter name)

**Key field name changes:**
- `credential_exchange_id` → `cred_ex_id`
- `presentation_exchange_id` → `pres_ex_id`
- `credential_definition_id` → `cred_def_id` (within filter)

### 5. Update State Handling Logic

Update your controller's state handling logic to account for v2.0 state names:

**Before (v1.0):**
- States use snake_case: `offer_sent`, `request_received`

**After (v2.0):**
- States use kebab-case: `offer-sent`, `request-received`, `credential-received`

**State name changes:**
- `offer_sent` → `offer-sent`
- `offer_received` → `offer-received`
- `request_sent` → `request-sent`
- `request_received` → `request-received`
- `credential_received` → `credential-received`
- `presentation_sent` → `presentation-sent`
- `presentation_received` → `presentation-received`

## Credential Management

As an issuer, you may need to revoke credentials that have been issued. AIP 2.0 supports credential revocation for both `indy` and `anoncreds` credential formats.

### Revoking Credentials

To revoke a credential, use the revocation endpoint that matches the filter used when the credential was issued:

**If credential was issued using `anoncreds` filter (askar-anoncreds wallet):**
```
POST /anoncreds/revocation/revoke
```

**If credential was issued using `indy` filter (askar wallet):**
```
POST /revocation/revoke
```

The endpoint you use depends on the filter used during issuance, not the credential format itself.

### Revocation Request Parameters

The simplest way to revoke a credential is using the `cred_ex_id` (credential exchange ID) from when the credential was issued:

```json
{
  "cred_ex_id": "cred-ex-456",
  "publish": true,
  "notify": true,
  "connection_id": "conn-123",
  "comment": "Credential revoked due to policy violation"
}
```

**Request parameters:**
- `cred_ex_id` (string, optional): Credential exchange ID from the issuance. If provided, revocation details are retrieved automatically.
- `rev_reg_id` (string, optional): Revocation registry ID. Required if `cred_ex_id` is not provided.
- `cred_rev_id` (string, optional): Credential revocation ID. Required if `cred_ex_id` is not provided.
- `publish` (boolean, optional): Whether to publish the revocation to the ledger immediately. Defaults to `false`. If `false`, revocation is marked as pending.
- `notify` (boolean, optional): Whether to send a revocation notification to the credential holder. Defaults to `false`.
- `connection_id` (string, optional): Connection ID of the credential holder. Required if `notify` is `true`.
- `notify_version` (string, optional): Version of revocation notification protocol to use. Defaults to `"v1_0"`.
- `comment` (string, optional): Optional comment explaining the reason for revocation.

### Revocation Workflow

1. **Revoke the credential** using the revocation endpoint with `cred_ex_id`
2. **Publish to ledger** by setting `publish: true` to immediately update the revocation registry on the VDR, or set `publish: false` to mark as pending
3. **Notify the holder** by setting `notify: true` and providing the `connection_id` to send a revocation notification

**Example: Revoking with immediate publication and notification**
```json
{
  "cred_ex_id": "cred-ex-456",
  "publish": true,
  "notify": true,
  "connection_id": "conn-123",
  "comment": "Credential expired"
}
```

**Example: Revoking and marking as pending (publish later)**
```json
{
  "cred_ex_id": "cred-ex-456",
  "publish": false,
  "notify": false
}
```

### Publishing Pending Revocations

If you revoked credentials with `publish: false`, you can publish all pending revocations later. Use the endpoint that matches the filter used when issuing:

**If credentials were issued using `anoncreds` filter (askar-anoncreds wallet):**
```
POST /anoncreds/revocation/publish-revocations
```

**If credentials were issued using `indy` filter (askar wallet):**
```
POST /revocation/publish-revocations
```

### Revocation Registries

When issuing credentials with revocation support, revocation registries are automatically created. These registries track the revocation status of credentials and are stored on a Verifiable Data Registry (VDR):

- **Revocation Registry Definition**: Defines the revocation registry and its parameters
- **Revocation Status Lists**: Published periodically to update the revocation status on the ledger
- **Tails Files**: Support files used for generating non-revocation proofs

### Verifier Considerations

When requesting presentations, verifiers can include `non_revoked` fields in presentation requests to verify that credentials haven't been revoked. See the [AnonCreds Specification - Create Presentation Request](https://anoncreds.github.io/anoncreds-spec/#create-presentation-request) for details on requesting non-revocation proofs.

For more details on revocation, see the [AnonCreds Specification](https://anoncreds.github.io/anoncreds-spec/) section on revocation.

## Additional Resources

- [Aries Interop Profile 2.0 Specification](https://github.com/decentralized-identity/aries-rfcs/tree/main/concepts/0302-aries-interop-profile)
- [ACA-Py Supported RFCs](SupportedRFCs.md)
- [ACA-Py Release Notes](../../CHANGELOG.md)
