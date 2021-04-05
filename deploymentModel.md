<!----- Conversion time: 2.418 seconds.
* Source doc: https://docs.google.com/a/cloudcompass.ca/open?id=1efPSAyhvOoJfaj3hS9iqsJbma3-4oc7l07uRPV1Gd9c

----->

# Aries Cloud Agent-Python (ACA-Py) - Deployment Model

This document is a "concept of operations" for an instance of an Aries cloud agent deployed from the primary artifact (a PyPi package) produced by this repo. In such a deployment there are **always** two components - a configured agent itself, and a controller that injects into that agent the business rules for the particular agent instance (see diagram).

![ACA-Py Deployment Overview](/docs/assets/deploymentModel-full.png "ACA-Py Deployment Overview")

The deployed agent messages with other agents via DIDComm protocols, and as events associated with those messages occur, sends webhook HTTP notifications to the controller. The agent also exposes for the controller's exclusive use an HTTP API covering all of the administrative handlers for those events. The controller receives the notifications from the agent, decides (with business rules - possible by asking a person using a UI) how to respond to the event and calls back to the agent via the HTTP API. Of course, the controller may also initiate events (e.g. messaging another agent) by calling that same API.

The following is an example of the interactions involved in creating a connection using the DIDComm "Establish Connection" protocol. The controller requests from the agent (via the administrative API) a connection invitation from the agent, and receives one back. The controller provides it to another agent (perhaps by displaying it in a QR code). Shortly after, the agent receives a DIDComm "Connection Request" message. The agent, sends it to the controller. The controller decides to accept the connection and calls the API with instructions to the agent to send a "Connection Response" message to the other agent. Since the controller always wants to know with whom a connection has been created, the controller also sends instructions to the agent (via the API, of course) to send a request presentation message to the new connection. And so on... During the interactions, the agent is tracking the state of the connections, and the state of the protocol instances (threads). Likewise, the controller may also be retaining state - after all, it's an application that could do anything.

Most developers will configure a "black box" instance of the ACA-Py. They need to know how it works, the DIDComm protocols it supports, the events it will generate and the administrative API it exposes. However, they don't need to drill into and maintain the ACA-Py code. Such developers will build controller applications (basically, traditional web apps) that at their simplest, use an HTTP interface to receive notification and send HTTP requests to the agent. It's the business logic implemented in, or accessed by the controller that gives the deployment its personality and role.

Note: the ACA-Py agent is designed to be stateless, persisting connection and protocol state to storage (such as Postgres database). As such, agents can be deployed to support horizontal scaling as necessary. Controllers can also be implemented to support horizontal scaling.

The sections below detail the internals of the ACA-Py and it's configurable elements, and the conceptual elements of a controller. There is no "Aries controller" repo to fork, as it is essentially just a web app. There are demos of using the elements in this repo, and several sample applications that you can use to get started on your on controller.

## Aries Cloud Agent

**Aries cloud agent** implement services to manage the execution of DIDComm messaging protocols for interacting with other DIDComm agents, and exposes an administrative HTTP API that supports a controller to direct how the agent should respond to messaging events. The agent relies on the controller to provide the business rules for handling the messaging events, and to initiate the execution of new DIDComm protocol instances. The internals of an ACA-Py instance is diagramed below.

![ACA-Py Agent Internals](/docs/assets/deploymentModel-agent.png "ACA-Py Agent Internals")

Instances of the Aries cloud agents are configured with the following sub-components:

- **Transport Plugins** - pluggable transport-specific message sender/receiver modules that interact with other agents. Messages outside the plugins are transport-agnostic JSON structures. Current modules include HTTP and WebSockets. In the future, we might add ZMQ, SMTP and so on.
- **Conductor** receives inbound messages from, and sends outbound messages to, the transport plugins. After internal processing, the conductor passes inbound messages to, and receives outbound messages from, the Dispatcher. In processing the messages, the conductor manages the message’s protocol instance thread state, retrieving the state on inbound messages and saving the state on outbound messages. The conductor handles generic decorators in messages such as verifying and generating signatures on message data elements, internationalization and so on.
- **Dispatcher** handles the distribution of messages to the DIDComm protocol message handlers and the responses received. The dispatcher passes to the conductor the thread state to be persistance and message data (if any) to be sent out from the Aries cloud agent instance.
- **DIDComm Protocols** - implement the DIDComm protocols supported by the agent instance, including the state object for the protocol, the DIDComm message handlers and the admin message handlers. Protocols are bundled as Python modules and loaded for during the agent deployment. Each protocol contributes the admin messages for the protocol to the controller REST interface. The protocols implement a number of events that invoke the controller via webhooks so that controller’s business logic can respond to the event.
- **Controller REST API** - a dynamically generated REST API (with a Swagger/OpenAPI user interface) based on the set of DIDComm protocols included in the agent deployment. The controller, activated via the webhooks from the protocol DIDComm message handlers, controls the Aries cloud agent by calling the REST API that invoke the protocol admin message handlers.
- **Handler API** - provides abstract interfaces to various handlers needed by the protocols and core Aries cloud agent components for accessing the secure storage (wallet), other storage, the ledger and so on. The API calls the handler implementations configured into the agent deployment.
- **Handler Plugins** - are the handler implementations called from the Handler API. The plugins may be internal to the Agent (in the same process space) or could be external (for example, in other processes/containers).
- **Secure Storage Plugin** - the Indy SDK is embedded in the Aries cloud agent and implements the default secure storage. An Aries cloud agent can be configured to use one of a number of indy-sdk storage implementations - in-memory, SQLite and Postgres at this time.
- **Ledger Interface Plugin** - In the current Aries cloud agent implementation, the Indy SDK provides an interface to an Indy-based public ledger for verifiable credential protocols. In future, ledger implementations (including those other than Indy) might be moved into the DIDComm protocol modules to be included as needed within a configured Aries cloud agent instance based on the DIDComm protocols used by the agent.

## Controller

A controller provides the personality of Aries cloud agent instance - the business logic (human, machine or rules driven) that drive the behaviour of the agent. The controller’s “Business Logic” in a cloud agent could be built into the controller app, could be an integration back to an enterprise system, or even a user interface for an individual. In all cases, the business logic provide responses to agent events or initiates agent actions. A deployed controller talks to a single Aries cloud agent deployment and manages the configuration of that agent. Both can be configured and deployed to support horizontal scaling.

![Controller Internals](/docs/assets/deploymentModel-controller.png "Controller Internals")

Generically, a controller is a web app invoked by HTTP webhook calls from its corresponding Aries cloud agent and invoking the DIDComm administration capabilities of the Aries cloud agent by calling the REST API exposed by that cloud agent. As well as responding to Aries cloud agent events, the controller initiates DIDComm protocol instances using the same REST API.

The controller and Aries cloud agent deployment **MUST** secure the HTTP interface between the two components. The interface provides the same HTTP integration between services as modern apps found in any enterprise today, and must be correspondingly secured.

A controller implements the following capabilities.

* **Initiator** - provides a mechanism to initiate new DIDComm protocol instances. The initiator invokes the REST API exposed by the Aries cloud agent to initiate the creation of a DIDComm protocol instance. For example, a permit-issuing service uses this mechanism to issue a Verifiable Credential associated with the issuance of a new permit.
* **Responder** - subscribes to and responds to events from the Aries cloud agent protocol message handlers, providing business-driven responses. The responder might respond immediately, or the event might cause a delay while the decision is determined, perhaps by sending the request to a person to decide. The controller may persist the event response state if the event is asynchronous - for example, when the event is passed to a person who may respond when they next use the web app.
* **Configuration** - manages the controller configuration data and the configuration of the Aries cloud agent.  Configuration in this context includes things like:
  * Credentials and Proof Requests to be Issued/Verified (respectively) by the Aries cloud agent.
  * The configuration of the webhook handler to which the responder subscribes.

While there are several examples of controllers, there is no “cookie cutter” repository to fork and customize. A controller is just a web service that receives HTTP requests (webhooks) and sends HTTP messages to the Aries cloud agent it controls via the REST API exposed by that agent.

## Deployment

The Aries cloud agent CI pipeline configured into the repository generates a PyPi package as an artifact. Implementers will generally have a controller repository, possibly copied from an existing controller instance, that has the code (business logic) for the controller and the configuration (transports, handlers, DIDComm protocols, etc.) for the Aries cloud agent instance. In the most common scenario, the Aries cloud agent and controller instances will be deployed based on the artifacts (e.g. container images) generated from that controller repository. With the simple HTTP-based interface between the controller and Aries cloud agent, both components can be horizontally scaled as needed, with a load balancer between the components. The configuration of the Aries cloud agent to use the Postgres wallet supports enterprise scale agent deployments.

Current examples of deployed instances of Aries cloud agent and controllers include:

* [indy-email-verification](https://github.com/bcgov/indy-email-verification) - a web app Controller that sends an email to a given email address with an embedded DIDComm invitation and on establishment of a connection, offers and provides the connected agent with an email control verifiable credential.
* [iiwbook](https://github.com/bcgov/iiwbook) - a web app Controller that on creation of a DIDComm connection, requests a proof of email control, and then sends to the connection a verifiable credential proving attendance at IIW. In between the proof and issuance is a human approval step using a simple web-based UI that implements a request queue.