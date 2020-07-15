# Aries Cloud Agent - Python: Clients

This folder contains language specific aca-py client (aka controller) implementations that wrap interactions with aca-py’s admin REST interface. The goal is to follow the semantics of the interface as close as possible, but to allow language specific deviations, or even be open to simplifications.

Examples:

Translate case styles. E.g. aca-py mostly uses snake case (credential_definition_id), whereas in Java the convention would be camel case (credentialDefinitionId).

Method naming. The proposal is to stick to the URL path wherever possible. E.g. a method to wrap /present-proof/send-proposal would be called presentProofSendProposal().

Allow simplification. Aca-pys request/response model allow a multitude of fields, but in most cases only a subset is mandatory. So, clients may reduce models to only mandatory fields to make interactions easier to understand. But they need to be aware that functionality might be lost.
