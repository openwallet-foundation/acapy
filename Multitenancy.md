# Multi-tenancy in ACA-Py <!-- omit in toc -->

Most deployments of ACA-Py use a single wallet for all operations. This means all connections, credentials, keys, and everything else is stored in the same wallet and shared between all controllers of the agent. Multi-tenancy in ACA-Py allows multiple tenants to use the same ACA-Py instance with a different context. All tenants get their own encrypted wallet that only holds their own data.

This allows ACA-Py to be used for a wider range of use cases. One use case could be a company that creates a wallet for each department. Each department has full control over the actions they perform while having a shared instance for easy maintenance. Another use case could be for a [Issuer-Hosted Custodial Agent](https://github.com/hyperledger/aries-rfcs/blob/master/concepts/0566-issuer-hosted-custodidal-agents/README.md). Sometimes it is required to host the agent on behalf of someone else.

## Table of Contents <!-- omit in toc -->

- [General Concept](#general-concept)
  - [Base and Sub Wallets](#base-and-sub-wallets)
  - [Usage](#usage)
- [Multi-tenant Admin API](#multi-tenant-admin-api)
- [Managed vs Unmanaged Mode](#managed-vs-unmanaged-mode)
  - [Managed](#managed)
  - [Unmanaged](#unmanaged)
  - [Usage](#usage-1)
- [Message Routing](#message-routing)
  - [Relaying](#relaying)
  - [Mediation](#mediation)
- [Webhooks](#webhooks)
  - [Webhook URLs](#webhook-urls)
  - [Identifying the wallet](#identifying-the-wallet)
- [Authentication](#authentication)
  - [Getting a token](#getting-a-token)
  - [JWT Secret](#jwt-secret)
  - [SwaggerUI](#swaggerui)

## General Concept

When multi-tenancy is enabled in ACA-Py there is still a single agent running, however, some of the resources are now shared between the tenants of the agent. Each tenant has their own wallet, with their own DIDs, connections, and credentials. Transports and most of the settings are still shared between agents. Each wallet uses the same endpoint, so to the outside world, it is not obvious multiple tenants are using the same agent.

### Base and Sub Wallets

Multi-tenancy in ACA-Py makes a distinction between a base wallet and sub wallets.

The wallets used by the different tenants are called **sub wallets**. A sub wallet is almost identical to a wallet when multi-tenancy is disabled. This means that you can do everything with it that a single-tenant ACA-Py instance can also do.

The **base wallet** however, takes on a different role and has limited functionality. Its main function is to manage the sub wallets, which can be done using the [Multi-tenant Admin API](#multi-tenant-admin-api). It stores all settings and information about the different sub wallets and will route incoming messages to the corresponding sub wallets. See [Message Routing](#message-routing) for more details. All other features are disabled for the base wallet. This means it cannot issue credentials, present proof, or do any of the other actions sub wallets can do. This is to keep a clear hierarchical difference between base and sub wallets

![Multi-tenancy Architecture](/docs/assets/multitenancyDiagram.png)

### Usage

Multi-tenancy is disabled by default. You can enable support for multiple wallets using the `--multitenant` startup parameter. To also be able to manage wallets for the tenants, the multi-tenant admin API can be enabled using the `--multitenant-admin` startup parameter. See [Multi-tenant Admin API](#multi-tenant-admin-api) below for more info on the admin API.

The `--jwt-secret` startup parameter is required when multi-tenancy is enabled. This is used for JWT creation and verification. See [Authentication](#authentication) below for more info.

Example:

```yaml
# This enables multi-tenancy in ACA-Py
multitenant: true

# This enables the admin API for multi-tenancy. More information below
multitenant-admin: true

# This sets the secret used for JWT creation/verification for sub wallets
jwt-secret: Something very secret
```

## Multi-tenant Admin API

The multi-tenant admin API allows you to manage wallets in ACA-Py. Only the base wallet can manage wallets, so you can't for example create a wallet in the context of sub wallet (using the `Authorization` header as specified in [Authentication](#authentication)).

Multi-tenancy related actions are grouped under the `/multitenancy` path or the `multitenancy` topic in the SwaggerUI. As mentioned above, the multi-tenant admin API is disabled by default, event when multi-tenancy is enabled. This is to allow for more flexible agent configuration (e.g. horizontal scaling where only a single instance exposes the admin API). To enable the multi-tenant admin API, the `--multitenant-admin` startup parameter can be used.

See the SwaggerUI for the exact API definition for multi-tenancy.

## Managed vs Unmanaged Mode

Multi-tenancy in ACA-Py is designed with two key management modes in mind.

### Managed

In **`managed`** mode, ACA-Py will manage the key for the wallet. This is the easiest configuration as it allows ACA-Py to fully control the wallet. When a message is received from another agent it can immediately unlock the wallet and process the message. The wallet key is stored encrypted in the base wallet.

### Unmanaged

In **`unmanaged`** mode, ACA-Py won't manage the key for the wallet. The key is not stored in the base wallet, which means the key to unlock the wallet needs to be provided whenever the wallet is used. When a message from another agent is received, ACA-Py cannot immediately unlock the wallet and process the message. See [Authentication](#authentication) for more info.

It is important to note unmanaged mode doesn't provide a lot of security over managed mode. The key is still processed by the agent, and therefore trust is required. It could however provide some benefit in the case a multi-tenant agent is compromised, as the agent doesn't store the key to unlock the wallet.

> :warning: Although support for unmanaged mode is mostly in place, the receiving of messages from other agents in unmanaged mode is not supported yet. This means unmanaged mode can not be used yet.

### Usage

The mode used can be specified when creating a wallet using the `key_management_mode` parameter.

```jsonc
// POST /multitenancy/wallet
{
  // ... other params ...
  "key_management_mode": "managed" // or "unmanaged"
}
```

## Message Routing

In multi-tenant mode, when ACA-Py receives a message from another agent, it will need to determine which tenant to route the message to. Hyperledger Aries defines two types of routing methods, mediation and relaying.

See the [Mediators and Relays](https://github.com/hyperledger/aries-rfcs/blob/master/concepts/0046-mediators-and-relays/README.md) RFC for an in-depth description of the difference between the two concepts.

### Relaying

In multi-tenant mode, ACA-Py still exposes a single endpoint for each transport. This means it can't route messages to sub wallets based on the endpoint. To resolve this the base wallet acts as a relay for all sub wallets. As can be seen in the architecture diagram above, all messages go through the base wallet. whenever a sub wallet creates a new key or connection, it will be registered at the base wallet. This allows the base wallet to look at the recipient keys for a message and determine which wallet it needs to route to.

### Mediation

ACA-Py allows messages to be routed through a mediator, and multi-tenancy can be used in combination with external mediators. The following scenarios are possible:

1. The base wallet has a default mediator set that will be used by sub wallets.
   - Use `--mediation-invitation` to connect to the mediator, request mediation, and set it as the default mediator
   - Use `default-mediator-id` if you're already connected to the mediator and mediation is granted (e.g. after restart).
   - When a sub wallet creates a connection or key it will be registered at the mediator via the base wallet connection. The base wallet will still act as a relay and route the messages to the correct sub wallets.
   - Pro: Not every wallet needs to create a connection with the mediator
   - Con: Sub wallets have no control over the mediator.
2. Sub wallet creates a connection with mediator and requests mediation
   - Use mediation as you would in a non-multi-tenant agent, however, the base wallet will still act as a relay.
   - You can set the default mediator to use for connections (using the mediation API).
   - Pro: Sub wallets have control over the mediator.
   - Con: Every wallet

The main tradeoff between option 1. and 2. is redundancy and control. Option 1. doesn't require every sub wallet to create a new connection with the mediator and request mediation. When all sub wallets are going to use the same mediator, this can be a huge benefit. Option 2. gives more control over the mediator being used. This could be useful if e.g. all wallets use a different mediator.

A combination of option 1. and 2. is also possible. In this case, two mediators will be used and the sub wallet mediator will forward to the base wallet mediator, which will, in turn, forward to the ACA-Py instance.

```
+---------------------+      +----------------------+      +--------------------+
| Sub wallet mediator | ---> | Base wallet mediator | ---> | Multi-tenant agent |
+---------------------+      +----------------------+      +--------------------+
```

## Webhooks

### Webhook URLs

ACA-Py makes use of [webhook events](./AdminAPI.md#administration-api-webhooks) to call back to the controller. Multiple webhook targets can be specified, however, in multi-tenant mode, it may be desirable to specify different webhook targets per wallet.

When creating a wallet `wallet_dispatch_type` be used to specify how webhooks for the wallet should be dispatched. The options are:

- `default`: Dispatch only to webhooks associated with this wallet.
- `base`: Dispatch only to webhooks associated with the base wallet.
- `both`: Dispatch to both webhook targets.

If either `default` or `both` is specified you can set the webhook URLs specific to this wallet using the `wallet.webhook_urls` option.

Example:

```jsonc
// POST /multitenancy/wallet
{
  // ... other params ...
  "wallet_dispatch_type": "default",
  "wallet_webhook_urls": [
    "https://webhook-url.com/path",
    "https://another-url.com/site"
  ]
}
```

### Identifying the wallet

When the webhook URLs of the base wallet are used or when multiple wallets specify the same webhook URL it can be hard to identify the wallet an event belongs to. To resolve this each webhook event will include the wallet id the event corresponds to.

For HTTP events the wallet id is included as the `x-wallet-id` header. For WebSockets, the wallet id is included in the enclosing JSON object.

HTTP example:

```jsonc
POST <webhook-url>/{topic} [headers=x-wallet-id]
{
    // event payload
}
```

WebSocket example:

```jsonc
{
  "topic": "{topic}",
  "wallet_id": "{wallet_id}",
  "payload": {
    // event payload
  }
}
```

## Authentication

When multi-tenancy is not enabled you can authenticate with the agent using the `x-api-key` header. As there is only a single wallet, this provides sufficient authentication and authorization.

For sub wallets, an additional authentication method is introduced using JSON Web Tokens (JWTs). A `token` parameter is returned after creating a wallet or calling the get token endpoint. This token must be provided for every admin API call you want to perform for the wallet using the Bearer authorization scheme.

Example

```
GET /connections [headers="Authorization: Bearer {token}]
```

The `Authorization` header is in addition to the Admin API key. So if the `admin-api-key` is enabled (which should be enabled in production) both the `Authorization` and the `x-api-key` headers should be provided when making calls to a sub wallet. For calls to a base wallet, only the `x-api-key` should be provided.

### Getting a token

A token can be obtained in two ways. The first method is the `token` parameter from the response of the create wallet (`POST /multitenancy/wallet`) endpoint. The second option is using the get wallet token endpoint (`POST /multitenancy/wallet/{wallet_id}/token`) endpoint.

In unmanaged mode, the get token endpoint also requires the `wallet_key` parameter to be included in the request body. The wallet key will be included in the JWT so the wallet can be unlocked when making requests to the admin API.

```jsonc
{
  "wallet_id": "wallet_id",
  // "wallet_key" in only present in unmanaged mode
  "wallet_key": "wallet_key"
}
```

> In unmanaged mode, sending the `wallet_key` to unlock the wallet in every request is not “secure” but keeps it simple at the moment. Eventually, the authentication method should be pluggable, and unmanaged mode would just mean that the key to unlock the wallet is not managed by ACA-Py.

### JWT Secret

For deterministic JWT creation and verification between restarts and multiple instances, the same JWT secret would need to be used. Therefore a `--jwt-secret` param is added to the ACA-Py agent that will be used for JWT creation and verification.

### SwaggerUI

When using the SwaggerUI you can click the :lock: icon next to each of the endpoints or the `Authorize` button at the top to set the correct authentication headers. Make sure to also include the `Bearer ` part in the input field. This won't be automatically added.

![](/docs/assets/adminApiAuthentication.png)
