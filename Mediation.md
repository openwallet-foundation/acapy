# Mediation docs

## Concepts
* **DIDComm Message Forwarding** - Sending an encrypted message to its recipient by first sending it to a third party responsible for forwarding the message on. Message contents are encrypted once for the recipient then wrapped in a [forward message](https://github.com/hyperledger/aries-rfcs/blob/master/concepts/0094-cross-domain-messaging/README.md#corerouting10forward) encrypted to the third party.
* **Mediator** - An agent that forwards messages to a client over a DIDComm connection.
* **Mediated Agent** or **Mediation client** - The agent(s) to which a mediator is willing to forward messages.
* **Mediation Request** - A message from a client to a mediator requesting mediation or forwarding.
* **Keylist** - The list of public keys used by the mediator to lookup to which connection a forward message should be sent. Each mediated agent is responsible for maintaining the keylist with the mediator.
* **Keylist Update** - A message from a client to a mediator informing the mediator of changes to the keylist.
* **Default Mediator** - A mediator to be used with with every newly created DIDComm connection. 
* **Mediation Connection** - Connection between the mediator and the mediated agent or client. Agents can use as many mediators as the identity owner sees fit. Requests for mediation are handled on a per connection basis.
* See [Aries RFC 0211: Coordinate Mediation Protocol](https://github.com/hyperledger/aries-rfcs/blob/master/features/0211-route-coordination/README.md) for additional details on message attributes and more.

## Command Line Arguments

* `--open-mediation` - Instructs mediators to automatically grant all incoming mediation requests.
* `--mediator-invitation` - Receive invitation, send mediation request and set as default mediator.
* `--default-mediator-id` - Set pre-existing mediator as default mediator.
* `--clear-default-mediator` - Clear the stored default mediator.

The minimum set of arguments *required* to enable mediation are:

```bash=
aca-py start ... \
    --open-mediation
```

To automate the mediation process on startup, *additionally* specify the following argument on the *mediated* agent (not the mediator):

```bash=
aca-py start ... \
    --mediator-invitation "<a multi-use invitation url from the mediator>"
```

If a default mediator has already been established, then the `--default-mediator-id` argument can be used *instead* of the `--mediator-invitation`.

## DIDComm Messages

See [Aries RFC 0211: Coordinate Mediation Protocol](https://github.com/hyperledger/aries-rfcs/blob/master/features/0211-route-coordination/README.md).
 
## Admin API

* `GET mediation/requests`
    * Return a list of all mediation records. Filter by `conn_id`, `state`, `mediator_terms` and `recipient_terms`.
* `GET mediation/requests/{mediation_id}`
    * Retrieve a mediation record by id.
* `DELETE mediation/requests/{mediation_id}`
    * Delete mediation record by id.
* `POST mediation/requests/{mediation_id}/grant`
    * As a mediator, grant a stored mediation request and send `granted` message to client.
* `POST mediation/requests/{mediation_id}/deny`
    * As a mediator, deny a stored mediation request and send `denied` message to client.
* `POST mediation/request/{conn_id}`
    * Send a mediation request to connection identified by the given connection ID.
* `GET mediation/keylists`
    * Returns key list associated with a connection. Filter on `client` for keys mediated by other agents and `server` for keys mediated by this agent.
* `POST mediation/keylists/{mediation_id}/send-keylist-update`
    * Send keylist update message to mediator identified by the given mediation ID. Updates contained in body of request.
* `POST mediation/keylists/{mediation_id}/send-keylist-query`
    * Send keylist query message to mediator identified by the given mediation ID.
* `GET mediation/default-mediator` **(PR pending)**
    * Retrieve the currently set default mediator.
* `PUT mediation/{mediation_id}/default-mediator` **(PR pending)**
    * Set the mediator identified by the given mediation ID as the default mediator.
* `DELETE mediation/default-mediator` **(PR pending)**
    * Clear the currently set default mediator (mediation status is maintained and remains functional, just not used as the default).

## Mediator Message Flow Overview

```plantuml
@startuml

' Make the notes not look so awful
skinparam useBetaStyle true
<style>
sequenceDiagram {
    note {
        BackGroundColor white
    }
}
</style>

actor  Alice     as Alice
entity Mediator  as Med
actor  Bob       as Bob
autonumber

== Arrange for Mediation with the Mediator ==

Alice <--> Med : Establish connection (details omitted)

loop until terms are acceptable
    Alice -> Med : Mediation Request
    note over Alice, Med: Establish terms of Mediation...
    Med -> Alice : Mediation deny
    note over Alice, Med: Mediation counter terms from Mediator
end

Alice <- Med : Mediation grant
note over Alice, Med
Mediator reports routing keys and endpoint to Alice.

{
    "@type": ".../coordinate-mediation/1.0/grant",
    "routing_keys": ["<mediator routing key>"],
    "endpoint": "<mediator's endpoint>"
}
end note

... Some time later ...

== Create a Mediated Connection ==
group Invitation
    Alice -> Alice : Create invitation

    Alice -> Med : Keylist update
    note over Alice, Bob
    Alice sends invitation key to mediator with keylist update message.
    
    { 
        "@type": ".../coordinate-mediation/1.0/keylist-update"
        "updates": [
            {
                "recipient_key": "<invitation key>",
                "action": "add"
            }
        ]
    }
    end note

    Alice --> Bob : Transmit Invitation (Out of Band)
    note over Alice, Bob
    Mediator routing keys and endpoint used for invitation.

    {
       "@type": ".../connections/1.0/invite",
       "routingKeys": ["<key sent to Alice in mediation grant>"],
       "recipientKeys": ["<key created by Alice for invitation>"],
       "serviceEndpoint": "<mediator's service endpoint>"
    }
    end note
end

group Connection Request
    Bob -> Bob : Create connection request
    Bob -> Bob : Prepare message for sending
    note right of Bob
    1. Encrypt request for Alice
    2. Wrap message in Forward Message
    3. Pop key from "routingKeys", Encrypt message for key
    4. Repeat for each remaining key in "routingKeys"
    end note

    Bob -> Med : Forward {Connection Request}
    note right
    Bob's response will be sent 
    to the mediator the mediator
    will forward response to Alice
    end note
    Med -> Med : Process Forward
    note right of Med
    1. Unpack message
    2. Inspect forward "to" field
    3. Look up key in routing tables
    end note
    Alice <- Med : Connection Request
end

group Connection Response
    Alice -> Alice : Create Response
    Alice -> Med : Keylist Update
    note over Alice, Bob
    Alice sends updates to mediator, including adding
    the new connection keys and removing invitation key.
    
    { 
        "@type": ".../coordinate-mediation/1.0/keylist-update"
        "updates": [
            {
                "recipient_key": "<new connection key>",
                "action": "add"
            },
            {
                "recipient_key": "<invitation key",
                "action": "remove"
            }
        ]
    }
    end note
    Alice -> Bob : Connection Response
    note left
    Connection response sent to
    Bob as normal. Sent DID Doc
    includes routing keys from
    the mediator and the mediator
    endpoint for the service
    endpoint.
    end note
end

== Mediation ==

Bob -> Med : Forward {Message}
note right
Messages are encrypted 
for Alice and then wrapped
in a forward message for
the Mediator.
end note

Alice <- Med : Message
note left
Mediator decrypts the forward 
message, inspects the "to",
and forwards to Alice.
Alice decrypts final message.
end note

Alice -> Bob : Message
note right
Outbound messages to Bob are sent
directly, not through Mediator.
end note

@enduml
```

## Using a Mediator
After establishing a connection with a mediator also having mediation granted, you can use that mediator id for future did_comm connections.
 When creating, receiving or accepting a invitation intended to be Mediated, you provide `mediation_id` with the desired mediator id. if using a single mediator for all future connections, You can set a default mediation id. If no mediation_id is provided the default mediation id will be used instead.