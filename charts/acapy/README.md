# AcaPy

![Version: 0.1.0](https://img.shields.io/badge/Version-0.1.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 1.2.2](https://img.shields.io/badge/AppVersion-1.2.2-informational?style=flat-square)

A Helm chart to deploy A Cloud Agent - Python.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure

## Installing the Chart

To install the chart with the release name `my-release`:

```console
helm repo add acapy	https://openwallet-foundation.github.io/acapy/
helm install my-release acapy/acapy
```

The command deploys AcaPY agent, along with PostgreSQL on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`


## Parameters

### Common parameters

| Name                  | Description                                                                                           | Value                   |
| --------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------- |
| `nameOverride`        | String to partially override fullname include (will maintain the release name)                        | `""`                    |
| `fullnameOverride`    | String to fully override fullname template                                                            | `""`                    |
| `namespaceOverride`   | String to fully override common.names.namespace                                                       | `""`                    |
| `kubeVersion`         | Force target Kubernetes version (using Helm capabilities if not set)                                  | `""`                    |
| `commonLabels`        | Labels to add to all deployed objects                                                                 | `{}`                    |
| `commonAnnotations`   | Annotations to add to all deployed objects                                                            | `{}`                    |
| `replicaCount`        | Number of AcaPy pods                                                                                  | `1`                     |
| `updateStrategy.type` | Set up update strategy for AcaPy installation.                                                        | `RollingUpdate`         |
| `image.registry`      | AcaPy image registry                                                                                  | `REGISTRY_NAME`         |
| `image.repository`    | AcaPy Image name                                                                                      | `REPOSITORY_NAME/AcaPy` |
| `image.digest`        | AcaPy image digest in the way sha256:aa.... Please note this parameter, if set, will override the tag | `""`                    |
| `image.pullPolicy`    | AcaPy image pull policy                                                                               | `IfNotPresent`          |
| `image.pullSecrets`   | Specify docker-registry secret names as an array                                                      | `[]`                    |

### Configuration files

Configuration file is mounted as is into the container. See the AcaPy documentation for details.
Note: Secure values of the configuration are passed via equivalent environment variables from secrets.

| Name                                              | Description                                                                                                                                                                                                                                                                                                                                                                                          | Value                          |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `argfile.yml.admin-insecure-mode`                 | Run the admin web server in insecure mode. DO NOT USE FOR PRODUCTION DEPLOYMENTS. The admin server will be publicly available to anyone who has access to the interface. An auto-generated admin API Key is supplied via `ACAPY-ADMIN-API-KEY`.                                                                                                                                                      | `false`                        |
| `argfile.yml.auto-accept-invites`                 | Automatically accept invites without firing a webhook event or waiting for an admin request. Default: false.                                                                                                                                                                                                                                                                                         | `true`                         |
| `argfile.yml.auto-accept-requests`                | Automatically accept connection requests without firing a webhook event or waiting for an admin request. Default: false.                                                                                                                                                                                                                                                                             | `true`                         |
| `argfile.yml.auto-create-revocation-transactions` | For Authors, specify whether to automatically create transactions for a cred def's revocation registry. (If not specified, the controller must invoke the endpoints required to create the revocation registry and assign to the cred def.)                                                                                                                                                          | `false`                        |
| `argfile.yml.auto-promote-author-did`             | For authors, specify whether to automatically promote a DID to the wallet public DID after writing to the ledger.``                                                                                                                                                                                                                                                                                  | `true`                         |
| `argfile.yml.auto-ping-connection`                | Automatically send a trust ping immediately after a connection response is accepted. Some agents require this before marking a connection as 'active'. Default: false.                                                                                                                                                                                                                               | `true`                         |
| `argfile.yml.auto-provision`                      | If the requested profile does not exist, initialize it with the given parameters.                                                                                                                                                                                                                                                                                                                    | `true`                         |
| `argfile.yml.auto-request-endorsement`            | For Authors, specify whether to automatically request endorsement for all transactions. (If not specified, the controller must invoke the request endorse operation for each transaction.)                                                                                                                                                                                                           | `false`                        |
| `argfile.yml.auto-respond-credential-offer`       | Automatically respond to Indy credential offers with a credential request. Default: false                                                                                                                                                                                                                                                                                                            | `true`                         |
| `argfile.yml.auto-respond-credential-proposal`    | Auto-respond to credential proposals with corresponding credential offers.                                                                                                                                                                                                                                                                                                                           | `false`                        |
| `argfile.yml.auto-respond-credential-request`     | Auto-respond to credential requests with corresponding credentials.                                                                                                                                                                                                                                                                                                                                  | `false`                        |
| `argfile.yml.auto-respond-presentation-proposal`  | Auto-respond to presentation proposals with corresponding presentation requests.                                                                                                                                                                                                                                                                                                                     | `true`                         |
| `argfile.yml.auto-respond-presentation-request`   | Automatically respond to Indy presentation requests with a constructed presentation if a corresponding credential can be retrieved for every referent in the presentation request. Default: false.                                                                                                                                                                                                   | `false`                        |
| `argfile.yml.auto-store-credential`               | Automatically store an issued credential upon receipt. Default: false.                                                                                                                                                                                                                                                                                                                               | `true`                         |
| `argfile.yml.auto-verify-presentation`            | Automatically verify a presentation when it is received. Default: false.                                                                                                                                                                                                                                                                                                                             | `false`                        |
| `argfile.yml.auto-write-transactions`             | For Authors, specify whether to automatically write any endorsed transactions. (If not specified, the controller must invoke the write transaction operation for each transaction.)                                                                                                                                                                                                                  | `false`                        |
| `argfile.yml.emit-new-didcomm-mime-type`          | Send packed agent messages with the DIDComm MIME type as of RFC 0044; i.e., 'application/didcomm-envelope-enc' instead of 'application/ssi-agent-wire'.                                                                                                                                                                                                                                              | `true`                         |
| `argfile.yml.emit-new-didcomm-prefix`             | Emit protocol messages with new DIDComm prefix; i.e., 'https://didcomm.org/' instead of (default) prefix 'did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/'.                                                                                                                                                                                                                                                     | `true`                         |
| `argfile.yml.endorser-alias`                      | For transaction Authors, specify the alias of the Endorser connection that will be used to endorse transactions.                                                                                                                                                                                                                                                                                     | `endorser`                     |
| `argfile.yml.endorser-protocol-role`              | Specify the role ('author' or 'endorser') which this agent will participate. Authors will request transaction endorsement from an Endorser. Endorsers will endorse transactions from Authors, and may write their own  transactions to the ledger. If no role (or 'none') is specified then the endorsement protocol will not be used and this agent will write transactions to the ledger directly. | `author`                       |
| `argfile.yml.auto-respond-messages`               | Automatically respond to basic messages indicating the message was received. Default: false.                                                                                                                                                                                                                                                                                                         | `true`                         |
| `argfile.yml.auto-verify-presentation`            | Automatically verify a presentation when it is received. Default: false.                                                                                                                                                                                                                                                                                                                             | `false`                        |
| `argfile.yml.genesis-transactions-list`           | Load YAML configuration for connecting to multiple HyperLedger Indy ledgers.                                                                                                                                                                                                                                                                                                                         | `/tmp/ledgers.yml`             |
| `argfile.yml.log-level`                           | Specifies a custom logging level as one of: ('debug', 'info', 'warning', 'error', 'critical')                                                                                                                                                                                                                                                                                                        | `info`                         |
| `argfile.yml.monitor-ping`                        | Send a webhook when a ping is sent or received.                                                                                                                                                                                                                                                                                                                                                      | `false`                        |
| `argfile.yml.multitenant-admin`                   | Specify whether to enable the multitenant admin api.                                                                                                                                                                                                                                                                                                                                                 | `false`                        |
| `argfile.yml.multitenant`                         | Enable multitenant mode.                                                                                                                                                                                                                                                                                                                                                                             | `false`                        |
| `argfile.yml.notify-revocation`                   | Specifies that aca-py will notify credential recipients when revoking a credential it issued.                                                                                                                                                                                                                                                                                                        | `false`                        |
| `argfile.yml.preserve-exchange-records`           | Keep credential exchange records after exchange has completed.                                                                                                                                                                                                                                                                                                                                       | `true`                         |
| `argfile.yml.requests-through-public-did`         | Must be set to true when using "implicit" invitations.                                                                                                                                                                                                                                                                                                                                               | `false`                        |
| `argfile.yml.public-invites`                      | Send invitations out using the public DID for the agent, and receive connection requests solicited by invitations which use the public DID. Default: false.                                                                                                                                                                                                                                          | `false`                        |
| `argfile.yml.read-only-ledger`                    | Sets ledger to read-only to prevent updates. Default: false.                                                                                                                                                                                                                                                                                                                                         | `true`                         |
| `argfile.yml.wallet-local-did`                    | If this parameter is set, provisions the wallet with a local DID from the '--seed' parameter, instead of a public DID to use with a Hyperledger Indy ledger. Default: false.                                                                                                                                                                                                                         | `true`                         |
| `argfile.yml.wallet-name`                         | Specifies the wallet name to be used by the agent. This is useful if your deployment has multiple wallets.                                                                                                                                                                                                                                                                                           | `askar-wallet`                 |
| `argfile.yml.wallet-storage-type`                 | Specifies the type of Indy wallet backend to use. Supported internal storage types are 'basic' (memory), 'default' (sqlite), and 'postgres_storage'.  The default, if not specified, is 'default'.                                                                                                                                                                                                   | `postgres_storage`             |
| `argfile.yml.wallet-type`                         | Specifies the type of Indy wallet provider to use. Supported internal storage types are 'basic' (memory) and 'indy'. The default (if not specified) is 'basic'.                                                                                                                                                                                                                                      | `askar`                        |
| `argfile.yml.webhook-url`                         | Send webhooks containing internal state changes to the specified URL. Optional API key to be passed in the request body can be appended using a hash separator [#]. This is useful for a controller to monitor agent events and respond to those events using the admin API. If not specified, webhooks are not published by the agent.                                                              | `{{ include "acapy.host" . }}` |
| `ledgers.yml`                                     |                                                                                                                                                                                                                                                                                                                                                                                                      | `{}`                           |
| `plugin-config.yml`                               | Plugin configuration file                                                                                                                                                                                                                                                                                                                                                                            | `{}`                           |
| `websockets.enabled`                              | Enable or disable the websocket transport for the agent.                                                                                                                                                                                                                                                                                                                                             | `false`                        |

### Wallet Storage configuration

Specifies the storage configuration to use for the wallet.
This is required if you are for using 'postgres_storage' wallet 'storage type.
For example, '{"url":"localhost:5432", "wallet_scheme":"MultiWalletSingleTable"}'.
This configuration maps to the indy sdk postgres plugin (PostgresConfig).

| Name                                  | Description                                                                                                                                                            | Value               |
| ------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `walletStorageConfig.json`            | Raw json, overrides all other values including postgres subchart values. e.g.: '{"url":"localhost:5432", "max_connections":"10", "wallet_scheme":"DatabasePerWallet"}' | `""`                |
| `walletStorageConfig.url`             | Database url. Overrides all other values including postgres subchart values.                                                                                           | `""`                |
| `walletStorageConfig.max_connections` | Client max connections, defaults to 10.                                                                                                                                | `10`                |
| `walletStorageConfig.wallet_scheme`   | Wallet scheme.                                                                                                                                                         | `DatabasePerWallet` |

### Wallet Storage Credentials

Specifies the storage credentials to use for the wallet.
This is required if you are for using 'postgres_storage' wallet 'storage type.
For example, '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}'.
This configuration maps to the indy sdk postgres plugin (PostgresCredential).
NOTE: admin_user must have the CREATEDB role or else initialization will fail.

| Name                                                   | Description                                                                                                                                                                                                                    | Value               |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------- |
| `walletStorageCredentials.json`                        | Raw json with database credentials. Overrides all other values including postgres subchart values. e.g.: '{"account":"postgres","password":"mysecretpassword","admin_account":"postgres","admin_password":"mysecretpassword"}' | `""`                |
| `walletStorageCredentials.account`                     | Database account name.                                                                                                                                                                                                         | `acapy`             |
| `walletStorageCredentials.admin_account`               | Database account with CREATEDB role used to create additional databases per wallet.                                                                                                                                            | `postgres`          |
| `walletStorageCredentials.admin_password`              | Database password for admin account.                                                                                                                                                                                           | `""`                |
| `walletStorageCredentials.existingSecret`              | Name of an existing secret containing 'database-user', 'database-password', 'admin-password' keys.                                                                                                                             | `""`                |
| `walletStorageCredentials.secretKeys.adminPasswordKey` | Key in existing secret containing admin password.                                                                                                                                                                              | `postgres-password` |
| `walletStorageCredentials.secretKeys.userPasswordKey`  | Key in existing secret containing password .                                                                                                                                                                                   | `password`          |

### Persistence

| Name                        | Description                          | Value               |
| --------------------------- | ------------------------------------ | ------------------- |
| `persistence.enabled`       | Enable persistence using PVC         | `true`              |
| `persistence.existingClaim` | Name of an existing PVC to use       | `""`                |
| `persistence.storageClass`  | PVC Storage Class for Tails volume   | `""`                |
| `persistence.accessModes`   | PVC Access Mode for Tails volume     | `["ReadWriteMany"]` |
| `persistence.size`          | PVC Storage Request for Tails volume | `1Gi`               |
| `persistence.annotations`   | Persistent Volume Claim annotations  | `{}`                |

### Service and Ports

| Name                               | Description                                                      | Value       |
| ---------------------------------- | ---------------------------------------------------------------- | ----------- |
| `service.type`                     | AcaPy service type                                               | `ClusterIP` |
| `service.ports.http`               | AcaPy service HTTP port                                          | `8021`      |
| `service.ports.admin`              | AcaPy service admin port                                         | `8022`      |
| `service.ports.ws`                 | AcaPy service websockets port                                    | `8023`      |
| `service.nodePorts.http`           | Node port for HTTP                                               | `""`        |
| `service.nodePorts.admin`          | Node port for admin                                              | `""`        |
| `service.nodePorts.ws`             | Node port for websockets                                         | `""`        |
| `service.sessionAffinity`          | Control where client requests go, to the same pod or round-robin | `None`      |
| `service.sessionAffinityConfig`    | Additional settings for the sessionAffinity                      | `{}`        |
| `service.clusterIP`                | AcaPy service Cluster IP                                         | `""`        |
| `service.loadBalancerIP`           | AcaPy service Load Balancer IP                                   | `""`        |
| `service.loadBalancerSourceRanges` | AcaPy service Load Balancer sources                              | `[]`        |
| `service.externalTrafficPolicy`    | AcaPy service external traffic policy                            | `Cluster`   |
| `service.annotations`              | Additional custom annotations for AcaPy service                  | `{}`        |
| `service.extraPorts`               | Extra port to expose on AcaPy service                            | `[]`        |

### Network Policy

| Name                                    | Description                                                                                                   | Value  |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ------ |
| `networkPolicy.enabled`                 | Specifies whether a NetworkPolicy should be created                                                           | `true` |
| `networkPolicy.allowExternal`           | Don't require server label for connections                                                                    | `true` |
| `networkPolicy.allowExternalEgress`     | Allow the pod to access any range of port and all destinations.                                               | `true` |
| `networkPolicy.addExternalClientAccess` | Allow access from pods with client label set to "true". Ignored if `networkPolicy.allowExternal` is true.     | `true` |
| `networkPolicy.extraIngress`            | Add extra ingress rules to the NetworkPolicy                                                                  | `[]`   |
| `networkPolicy.extraEgress`             | Add extra ingress rules to the NetworkPolicy                                                                  | `[]`   |
| `networkPolicy.ingressPodMatchLabels`   | Labels to match to allow traffic from other pods. Ignored if `networkPolicy.allowExternal` is true.           | `{}`   |
| `networkPolicy.ingressNSMatchLabels`    | Labels to match to allow traffic from other namespaces. Ignored if `networkPolicy.allowExternal` is true.     | `{}`   |
| `networkPolicy.ingressNSPodMatchLabels` | Pod labels to match to allow traffic from other namespaces. Ignored if `networkPolicy.allowExternal` is true. | `{}`   |

### Ingress and Endpoint configuration

| Name                             | Description                                                                                                                      | Value                    |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `agentUrl`                       | must be set if ingress is not enabled                                                                                            | `""`                     |
| `adminUrl`                       | must be set if ingress is not enabled                                                                                            | `""`                     |
| `ingress.agent.enabled`          | Set to true to enable ingress record generation                                                                                  | `false`                  |
| `ingress.agent.pathType`         | Ingress Path type                                                                                                                | `ImplementationSpecific` |
| `ingress.agent.apiVersion`       | Override API Version (automatically detected if not set)                                                                         | `""`                     |
| `ingress.agent.hostname`         | When the ingress is enabled, a host pointing to this will be created                                                             | `acapy.local`            |
| `ingress.agent.path`             | Default path for the ingress resource                                                                                            | `/`                      |
| `ingress.agent.annotations`      | Additional annotations for the Ingress resource. To enable certificate autogeneration, place here your cert-manager annotations. | `{}`                     |
| `ingress.agent.tls`              | Enable TLS configuration for the hostname defined at ingress.hostname parameter                                                  | `false`                  |
| `ingress.agent.extraHosts`       | The list of additional hostnames to be covered with this ingress record.                                                         | `[]`                     |
| `ingress.agent.extraPaths`       | Any additional arbitrary paths that may need to be added to the ingress under the main host.                                     | `[]`                     |
| `ingress.agent.extraTls`         | The tls configuration for additional hostnames to be covered with this ingress record.                                           | `[]`                     |
| `ingress.agent.secrets`          | If you're providing your own certificates, please use this to add the certificates as secrets                                    | `[]`                     |
| `ingress.agent.secrets`          | It is also possible to create and manage the certificates outside of this helm chart                                             | `[]`                     |
| `ingress.agent.selfSigned`       | Create a TLS secret for this ingress record using self-signed certificates generated by Helm                                     | `false`                  |
| `ingress.agent.ingressClassName` | IngressClass that will be be used to implement the Ingress (Kubernetes 1.18+)                                                    | `""`                     |
| `ingress.agent.extraRules`       | Additional rules to be covered with this ingress record                                                                          | `[]`                     |
| `ingress.admin.enabled`          | Set to true to enable ingress record generation                                                                                  | `false`                  |
| `ingress.admin.pathType`         | Ingress Path type                                                                                                                | `ImplementationSpecific` |
| `ingress.admin.apiVersion`       | Override API Version (automatically detected if not set)                                                                         | `""`                     |
| `ingress.admin.hostname`         | When the ingress is enabled, a host pointing to this will be created                                                             | `admin.acapy.local`      |
| `ingress.admin.path`             | Default path for the ingress resource                                                                                            | `/`                      |
| `ingress.admin.annotations`      | Additional annotations for the Ingress resource. To enable certificate autogeneration, place here your cert-manager annotations. | `{}`                     |
| `ingress.admin.tls`              | Enable TLS configuration for the hostname defined at ingress.hostname parameter                                                  | `false`                  |
| `ingress.admin.extraHosts`       | The list of additional hostnames to be covered with this ingress record.                                                         | `[]`                     |
| `ingress.admin.extraPaths`       | Any additional arbitrary paths that may need to be added to the ingress under the main host.                                     | `[]`                     |
| `ingress.admin.extraTls`         | The tls configuration for additional hostnames to be covered with this ingress record.                                           | `[]`                     |
| `ingress.admin.secrets`          | If you're providing your own certificates, please use this to add the certificates as secrets                                    | `[]`                     |
| `ingress.admin.secrets`          | It is also possible to create and manage the certificates outside of this helm chart                                             | `[]`                     |
| `ingress.admin.selfSigned`       | Create a TLS secret for this ingress record using self-signed certificates generated by Helm                                     | `false`                  |
| `ingress.admin.ingressClassName` | IngressClass that will be be used to implement the Ingress (Kubernetes 1.18+)                                                    | `""`                     |
| `ingress.admin.extraRules`       | Additional rules to be covered with this ingress record                                                                          | `[]`                     |

### Deployment parameters

| Name                                 | Description                                                                                                                                                                                                       | Value           |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------- |
| `resourcesPreset`                    | Set container resources according to one common preset (allowed values: none, nano, micro, small, medium, large, xlarge, 2xlarge). This is ignored if resources is set (resources is recommended for production). | `none`          |
| `resources`                          | Set container requests and limits for different resources like CPU or memory (essential for production workloads)                                                                                                 | `{}`            |
| `livenessProbe.enabled`              | Enable livenessProbe                                                                                                                                                                                              | `true`          |
| `livenessProbe.initialDelaySeconds`  | Initial delay seconds for livenessProbe                                                                                                                                                                           | `30`            |
| `livenessProbe.periodSeconds`        | Period seconds for livenessProbe                                                                                                                                                                                  | `20`            |
| `livenessProbe.timeoutSeconds`       | Timeout seconds for livenessProbe                                                                                                                                                                                 | `10`            |
| `livenessProbe.failureThreshold`     | Failure threshold for livenessProbe                                                                                                                                                                               | `6`             |
| `livenessProbe.successThreshold`     | Success threshold for livenessProbe                                                                                                                                                                               | `1`             |
| `livenessProbe.httpGet.path`         | Request path for livenessProbe                                                                                                                                                                                    | `/status/live`  |
| `livenessProbe.httpGet.port`         | Port for livenessProbe                                                                                                                                                                                            | `admin`         |
| `readinessProbe.enabled`             | Enable readinessProbe                                                                                                                                                                                             | `true`          |
| `readinessProbe.initialDelaySeconds` | Initial delay seconds for readinessProbe                                                                                                                                                                          | `5`             |
| `readinessProbe.periodSeconds`       | Period seconds for readinessProbe                                                                                                                                                                                 | `10`            |
| `readinessProbe.timeoutSeconds`      | Timeout seconds for readinessProbe                                                                                                                                                                                | `5`             |
| `readinessProbe.failureThreshold`    | Failure threshold for readinessProbe                                                                                                                                                                              | `6`             |
| `readinessProbe.successThreshold`    | Success threshold for readinessProbe                                                                                                                                                                              | `1`             |
| `readinessProbe.httpGet.path`        | Request path for readinessProbe                                                                                                                                                                                   | `/status/ready` |
| `readinessProbe.httpGet.port`        | Port for readinessProbe                                                                                                                                                                                           | `admin`         |
| `initContainers`                     | Add additional init containers for the hidden node pod(s)                                                                                                                                                         | `[]`            |
| `extraArgs`                          | Array containing extra command line arguments to configure aca-py                                                                                                                                                 | `[]`            |
| `extraEnvVarsCM`                     | Name of existing ConfigMap containing extra env vars                                                                                                                                                              | `""`            |
| `extraEnvVarsSecret`                 | Name of existing Secret containing extra env vars                                                                                                                                                                 | `""`            |
| `extraEnvVars`                       | Array containing extra env vars to configure AcaPy                                                                                                                                                                | `[]`            |
| `nodeAffinityPreset.type`            | Node affinity preset type. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                                                                                                         | `""`            |
| `nodeAffinityPreset.key`             | Node label key to match Ignored if `affinity` is set.                                                                                                                                                             | `""`            |
| `nodeAffinityPreset.values`          | Node label values to match. Ignored if `affinity` is set.                                                                                                                                                         | `[]`            |
| `affinity`                           | Affinity for pod assignment                                                                                                                                                                                       | `{}`            |
| `podAffinityPreset`                  | Pod affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                                                                                                               | `""`            |
| `podAntiAffinityPreset`              | Pod anti-affinity preset. Ignored if `affinity` is set. Allowed values: `soft` or `hard`                                                                                                                          | `soft`          |
| `nodeSelector`                       | Node labels for pod assignment                                                                                                                                                                                    | `{}`            |
| `tolerations`                        | Tolerations for pod assignment                                                                                                                                                                                    | `[]`            |
| `topologySpreadConstraints`          | Topology spread constraints rely on node labels to identify the topology domain(s) that each Node is in                                                                                                           | `[]`            |
| `podLabels`                          | Pod labels                                                                                                                                                                                                        | `{}`            |
| `podAnnotations`                     | Pod annotations                                                                                                                                                                                                   | `{}`            |
| `extraVolumes`                       | Array of extra volumes to be added to the deployment (evaluated as template). Requires setting `extraVolumeMounts`                                                                                                | `[]`            |
| `extraVolumeMounts`                  | Array of extra volume mounts to be added to the container (evaluated as template). Normally used with `extraVolumes`.                                                                                             | `[]`            |
| `extraDeploy`                        | Array of extra objects to deploy with the release                                                                                                                                                                 | `[]`            |

### PostgreSQL Parameters


### Autoscaling

| Name                                                        | Description                                                                                  | Value   |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ------- |
| `autoscaling.enabled`                                       | Enable Horizontal POD autoscaling for AcaPy                                                  | `false` |
| `autoscaling.minReplicas`                                   | Minimum number of AcaPy replicas                                                             | `1`     |
| `autoscaling.maxReplicas`                                   | Maximum number of AcaPy replicas                                                             | `10`    |
| `autoscaling.targetCPUUtilizationPercentage`                | Target CPU utilization percentage                                                            | `80`    |
| `autoscaling.targetMemoryUtilizationPercentage`             | Target Memory utilization percentage                                                         | `80`    |
| `autoscaling.behavior.scaleUp.stabilizationWindowSeconds`   | The number of seconds for which past recommendations should be considered while scaling up   | `60`    |
| `autoscaling.behavior.scaleUp.selectPolicy`                 | The priority of policies that the autoscaler will apply when scaling up                      | `Max`   |
| `autoscaling.behavior.scaleUp.policies`                     | HPA scaling policies when scaling up                                                         | `[]`    |
| `autoscaling.behavior.scaleDown.stabilizationWindowSeconds` | The number of seconds for which past recommendations should be considered while scaling down | `120`   |
| `autoscaling.behavior.scaleDown.selectPolicy`               | The priority of policies that the autoscaler will apply when scaling down                    | `Max`   |
| `autoscaling.behavior.scaleDown.policies`                   | HPA scaling policies when scaling down                                                       | `[]`    |

### RBAC and Security settings

| Name                                                | Description                                               | Value            |
| --------------------------------------------------- | --------------------------------------------------------- | ---------------- |
| `serviceAccount.create`                             | Enable creation of ServiceAccount for acapy pod           | `true`           |
| `serviceAccount.name`                               | The name of the ServiceAccount to use.                    | `""`             |
| `serviceAccount.annotations`                        | Annotations for service account. Evaluated as a template. | `{}`             |
| `serviceAccount.automountServiceAccountToken`       | Auto-mount token for the Service Account                  | `false`          |
| `automountServiceAccountToken`                      | Auto-mount token in pod                                   | `false`          |
| `podSecurityContext.enabled`                        | Enable securityContext on for AcaPy deployment            | `true`           |
| `podSecurityContext.fsGroupChangePolicy`            | Set filesystem group change policy                        | `Always`         |
| `podSecurityContext.sysctls`                        | Set kernel settings using the sysctl interface            | `[]`             |
| `podSecurityContext.supplementalGroups`             | Set filesystem extra groups                               | `[]`             |
| `podSecurityContext.fsGroup`                        | Group to configure permissions for volumes                | `1001`           |
| `containerSecurityContext.enabled`                  | Enabled containers' Security Context                      | `true`           |
| `containerSecurityContext.seLinuxOptions`           | Set SELinux options in container                          | `{}`             |
| `containerSecurityContext.runAsUser`                | Set containers' Security Context runAsUser                | `1001`           |
| `containerSecurityContext.runAsGroup`               | Set containers' Security Context runAsGroup               | `1001`           |
| `containerSecurityContext.runAsNonRoot`             | Set container's Security Context runAsNonRoot             | `true`           |
| `containerSecurityContext.privileged`               | Set container's Security Context privileged               | `false`          |
| `containerSecurityContext.readOnlyRootFilesystem`   | Set container's Security Context readOnlyRootFilesystem   | `true`           |
| `containerSecurityContext.allowPrivilegeEscalation` | Set container's Security Context allowPrivilegeEscalation | `false`          |
| `containerSecurityContext.capabilities.drop`        | List of capabilities to be dropped                        | `["ALL"]`        |
| `containerSecurityContext.seccompProfile.type`      | Set container's Security Context seccomp profile          | `RuntimeDefault` |

### PostgreSQL Parameters

| Name                                                  | Description                                                                                                                                                                                                                | Value                    |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| `postgresql.enabled`                                  | Switch to enable or disable the PostgreSQL helm chart                                                                                                                                                                      | `true`                   |
| `postgresql.auth.username`                            | Name for a custom user to create                                                                                                                                                                                           | `acapy`                  |
| `postgresql.auth.database`                            | Name for a custom database to create                                                                                                                                                                                       | `""`                     |
| `postgresql.auth.enablePostgresUser`                  | Assign a password to the "postgres" admin user. Otherwise, remote access will be blocked for this user. Not recommended for production deployments.                                                                        | `true`                   |
| `postgresql.auth.existingSecret`                      | Name of existing secret to use for PostgreSQL credentials                                                                                                                                                                  | `""`                     |
| `postgresql.architecture`                             | PostgreSQL architecture (`standalone` or `replication`)                                                                                                                                                                    | `standalone`             |
| `postgresql.primary.persistence.enabled`              | Enable PostgreSQL Primary data persistence using PVC                                                                                                                                                                       | `true`                   |
| `postgresql.primary.persistence.size`                 | PVC Storage Request for PostgreSQL volume                                                                                                                                                                                  | `1Gi`                    |
| `postgresql.primary.containerSecurityContext.enabled` | Enable container security context                                                                                                                                                                                          | `false`                  |
| `postgresql.primary.podSecurityContext.enabled`       | Enable security context                                                                                                                                                                                                    | `false`                  |
| `postgresql.primary.resourcesPreset`                  | Set container resources according to one common preset (allowed values: none, nano, small, medium, large, xlarge, 2xlarge). This is ignored if primary.resources is set (primary.resources is recommended for production). | `nano`                   |
| `postgresql.primary.resources`                        | Set container requests and limits for different resources like CPU or memory (essential for production workloads)                                                                                                          | `{}`                     |
| `postgresql.primary.extendedConfiguration`            | Extended PostgreSQL Primary configuration (appended to main or default configuration)                                                                                                                                      | `max_connections = 500
` |

...
