# ACA-Py Administration API

## Using the OpenAPI (Swagger) Interface

ACA-Py provides an OpenAPI-documented REST interface for adminstering the agent's internal state and sparking communication with connected agents.

To see the specifics of the supported endpoints as well as the expected request and response formats it is recommended to run the `aca-py` agent with the `--admin {HOST} {PORT}` and `--admin-insecure-mode` command line parameters, which exposes the OpenAPI UI on the provided port for interaction via a web browser. Production deployments should run the agent with `--admin-api-key {KEY}` and add the `X-API-Key: {KEY}` header to all requests instead of running the agent with the `--admin-insecure-mode` parameter.

![Admin API Screenshot](/docs/assets/adminApi.png)

To invoke a specific method:

 * scroll to and find that endpoint;
 * click on the endpoint name to expand its section of the UI;
 * click on the Try it out button;
 * fill in any data necessary to run the command;
 * click Execute;
 * check the response to see if the request worked as expected.

The mechanical steps are easy, it’s fourth step from the list above that can be tricky. Supplying the right data and, where JSON is involved, getting the syntax correct - braces and quotes can be a pain. When steps don’t work, start your debugging by looking at your JSON. You may also choose to use a REST client like Postman or Insomnia which will provide syntax highlighting and other features to simplify the process.

Because API methods will often kick off asynchronous processes, the JSON response provided by an endpoint is not always sufficient to determine the next action. To handle this situation as well as events triggered due to external inputs (such as new connection requests), it is necessary to implement a webhook processor, as detailed in the next section.

The combination of an OpenAPI client and webhook processor is referred to as an ACA-Py Controller and is the recommended method to define custom behaviours for your ACA-Py-based agent application.

## Administration API Webhooks

When ACA-Py is started with the `--webhook-url {URL}` command line parameter, state-management records are sent to the provided URL via POST requests whenever a record is created or its `state` property is updated.

When a webhook is dispatched, the record `topic` is appended as a path component to the URL, for example: `https://webhook.host.example` becomes `https://webhook.host.example/connections` when a connection record is updated. A POST request is made to the resulting URL with the body of the request comprised by a serialized JSON object. The full set of properties of the current set of webhook payloads are listed below. Note that empty (null-value) properties are omitted.

#### Pairwise Connection Record Updated (`/connections`)

 * `connection_id`: the unique connection identifier
 * `state`: `init` / `invitation` / `request` / `response` / `active` / `error` / `inactive`
 * `my_did`: the DID this agent is using in the connection
 * `their_did`: the DID the other agent in the connection is using
 * `their_label`: a connection label provided by the other agent
 * `their_role`: a role assigned to the other agent in the connection
 * `inbound_connection_id`: a connection identifier for the related inbound routing connection
 * `initiator`: `self` / `external` / `multiuse`
 * `invitation_key`: a verification key used to identify the source connection invitation
 * `request_id`: the `@id` property from the connection request message
 * `routing_state`: `none` / `request` / `active` / `error`
 * `accept`: `manual` / `auto`
 * `error_msg`: the most recent error message
 * `invitation_mode`: `once` / `multi`
 * `alias`: a local alias for the connection record

#### Basic Message Received (`/basicmessages`)

 * `connection_id`: the identifier of the related pairwise connection
 * `message_id`: the `@id` of the incoming agent message
 * `content`: the contents of the agent message
 * `state`: `received`

#### Credential Exchange Record Updated (`/issue_credential`)

* `credential_exchange_id`: the unique identifier of the credential exchange
* `connection_id`: the identifier of the related pairwise connection
* `thread_id`: the thread ID of the previously received credential proposal or offer
* `parent_thread_id`: the parent thread ID of the previously received credential proposal or offer
* `initiator`: issue-credential exchange initiator `self` / `external`
* `state`: `proposal_sent` / `proposal_received` / `offer_sent` / `offer_received` / `request_sent` / `request_received` / `issued` / `credential_received` / `stored`
* `credential_definition_id`: the ledger identifier of the related credential definition
* `schema_id`: the ledger identifier of the related credential schema
* `credential_proposal_dict`: the credential proposal message
* `credential_offer`: (Indy) credential offer
* `credential_request`: (Indy) credential request
* `credential_request_metadata`: (Indy) credential request metadata
* `credential_id`: the wallet identifier of the stored credential
* `raw_credential`: the credential record as received
* `credential`: the credential record as stored in the wallet
* `auto_offer`: (boolean) whether to automatically offer the credential
* `auto_issue`: (boolean) whether to automatically issue the credential
* `error_msg`: the previous error message

#### Presentation Exchange Record Updated (`/present_proof`)

 * `presentation_exchange_id`: the unique identifier of the presentation exchange
 * `connection_id`: the identifier of the related pairwise connection
 * `thread_id`: the thread ID of the previously received presentation proposal or offer
 * `initiator`: present-proof exchange initiator: `self` / `external`
 * `state`: `proposal_sent` / `proposal_received` / `request_sent` / `request_received` / `presentation_sent` / `presentation_received` / `verified`
 * `presentation_proposal_dict`: the presentation proposal message
 * `presentation_request`: (Indy) presentation request (also known as proof request)
 * `presentation`: (Indy) presentation (also known as proof)
 * `verified`: (string) whether the presentation is verified: `true` or `false`
 * `auto_present`: (boolean) prover choice to auto-present proof as verifier requests
 * `error_msg`: the previous error message
