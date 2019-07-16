<!----- Conversion time: 3.631 seconds.

Source doc: https://docs.google.com/a/cloudcompass.ca/open?id=12N1KDm1l4Az6bSOJ3DVnBs4HC3_TWz9VpIQ6WTEeykw

----->

# Aries OpenAPI Demo <!-- omit in toc -->

This demo is for developers comfortable with playing around with APIs using the OpenAPI (Swagger) user interface and JSON. The controller for each of the two agent instances in the demo is you. You drive the API exposed by the agent instances to respond to events received by each agent. The demo covers two agents, Alice and Faber (the usual two suspects). The two agents connect, and then the Faber agent issues an Education credential to Alice, and then asks Alice to prove she possesses the credential. Who knows why Faber needs to get the proof, but it lets us show off more protocols.

# Table of Contents <!-- omit in toc -->

- [Running in a Browser](#Running-in-a-Browser)
- [Running in Docker](#Running-in-Docker)
  - [Starting Up](#Starting-Up)
  - [Start the VON Network](#Start-the-VON-Network)
  - [Running the Faber Agent](#Running-the-Faber-Agent)
  - [Running Alice’s Agent](#Running-Alices-Agent)
  - [Restarting the Docker Containers](#Restarting-the-Docker-Containers)
- [Using the Swagger User Interface](#Using-the-Swagger-User-Interface)
- [Establishing a Connection](#Establishing-a-Connection)
  - [Notes](#Notes)
- [Preparing to Issue a Credential](#Preparing-to-Issue-a-Credential)
  - [Register the Faber DID](#Register-the-Faber-DID)
  - [Publish the Schema](#Publish-the-Schema)
  - [Publishing a Credential Definition](#Publishing-a-Credential-Definition)
  - [Notes](#Notes-1)
- [Issuing a Credential](#Issuing-a-Credential)
  - [Notes](#Notes-2)
  - [Bonus Points](#Bonus-Points)
- [Requesting/Presenting a Proof](#RequestingPresenting-a-Proof)
  - [Notes](#Notes-3)
- [Conclusion](#Conclusion)


## Running in a Browser

We will get started by getting three browser tabs ready that will be used throughout the lab. Two will be Swagger UIs for the Faber and Alice Agent and one for the Public Ledger (showing the Hyperledger Indy ledger).

In your browser, go to the docker playground service [Play with VON](http://play-with-von.vonx.io) (from the BC Gov). On the title screen, click "Start". On the next screen, click (in the left menu) "+Add a new instance".  That will start up a terminal in your browser. Run the following commands to start the Faber agent. It is not a typo that the last line has "faber" in it.  We're just borrowing that script to get started.

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo faber
```

Once the Faber agent has started up (with the invite displayed), click the link near the top of the screen `8021`. That will start an instance of the OpenAPI User Interface connected to the Faber instance. Note that the URL on the Swagger instance is `http://ip....8021.direct...`.

**Remember that the Swagger browser tab with an address containing 8021 is the Faber's agent.**

Now to start Alice's agent. Click the "+Add a new instance" button again to open another terminal session. Run the following commands to start Alice's agent:

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
LEDGER_URL=http://dev.greenlight.bcovrin.vonx.io ./run_demo alice
```

Once the Alice agent has started up (with the `invite:` prompt displayed), click the link near the top of the screen `8031`. That will start an instance of the OpenAPI User Interface connected to the Alice instance. Note that the URL on the Swagger instance is `http://ip....8031.direct...`.

**Remember that the Swagger browser tab with an address containing 8031 is Alice's agent.**

Finally, open up a third browser tab and navigate to [http://dev.greenlight.bcovrin.vonx.io](http://dev.greenlight.bcovrin.vonx.io). This will be called the "Ledger tab" in the instructions below.

You are ready to go. Skip down to the [Using the Swagger User Interface](using-the-swagger-user-interface) section.

## Running in Docker

We will get started by getting three browser tabs ready that will be used throughout the lab. Two will be Swagger UIs for the Faber and Alice Agent and one for the Public Ledger (showing the Hyperledger Indy ledger).

To run the demo, you must have a system capable of running docker to run containers, and terminal windows running bash. On Windows systems, we highly recommend using git-bash, the Windows Subsystem for Linux (WSL) or a comparable facility. The demo will not work using PowerShell.

Before beginning, clone, or fork and clone this repo and the [von-network](https://github.com/bcgov/von-network) repo.

### Starting Up

To begin the running the demo in Docker, open up three terminal windows, one to run a local Indy network (using the VON network) and one each for the Faber’s and Alice’s agent. You’ll also open up three browser tabs, one to allow browsing the Public Ledger (`von-network`), and one for the Swagger user interface for each of the agents.

### Start the VON Network

In one of the terminal windows, follow the [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) instructions to start (but don’t stop) a local four-node Indy network. In one of the browser tabs, navigate to [http://localhost:9000](http://localhost:9000) to see the Public Ledger  user interface and to verify the Indy network is running.

> NOTE: The use of localhost for the Web interfaces is assumed in this tutorial. If your docker setup is atypical, you may use a different address for your docker host.

### Running the Faber Agent

To start the Faber agent, open up a second terminal window and in it change directory to the `demo` folder of your clone of this repo and execute the following command. It is not a typo that the command has "faber" in it.  We're just borrowing that script to get started.

```bash
./run_demo faber
```

If all goes well, the agent will show a message indicating it is running. Use the second of the browser tabs to navigate to [http://localhost:8021](http://localhost:8021). You should see an OpenAPI user interface with a (long-ish) list of API endpoints. These are the endpoints exposed by the Faber Agent.

**Remember that the browser tab with an address containing 8021 Swagger is the Faber agent.**

### Running Alice’s Agent

To start the Alice's agent, open up a third terminal window and in it change directory to the `demo` folder of your clone of this repo and execute the following command.

``` bash
./run_demo alice
```

If all goes well, the agent will show a message indicating it is running. Open a third browser tab to navigate to [http://localhost:8031](http://localhost:8031). Again, you should see the Swagger user interface with a list of API endpoints, this time the endpoints for Alice’s agent.

**Remember that the browser tab with an address containing 8031 Swagger is the Alice agent.**

### Restarting the Docker Containers

When you are done, or to stop the demo so you can restart it, carry out the following steps:

1. In the Faber and Alice agent terminal windows, hit Ctrl-C to terminate the agents.
2. In the `von-network` terminal window, hit Ctrl-C to stop the logging, and then run the command `./manage down` to both stop the network and remove the data on the ledger. 

## Using the Swagger User Interface

The demo is run entirely in the browser tabs you've already opened - Faber, Alice and the Indy Public Ledger. The agent terminal windows will only show messages if an error occurs in using the REST API. The Indy public ledger terminal window will display a log of messages from the four nodes of the Indy network. In the instructions that follow, we’ll let you know if you need to be in the Faber, Alice or Indy browser tab. We’ll leave it to you to track which is which.

Using the OpenAPI user interface is pretty simple. In the steps below, we’ll indicate what API endpoint you need use, such as **`POST /connections/create-invitation`**. That means you must:

1. Scroll to and find that endpoint.
2. Click on the endpoint name to expand its section of the UI.
3. Click on the `Try it now` button.
4. Fill in any data necessary to run the command.
5. Click `Execute`
6. Check the response to see if the request worked.

So, the mechanical steps are easy. It’s fourth step from the list above that can be tricky. Supplying the right data and, where JSON is involved, getting the syntax correct - braces and quotes. When steps don’t work, start your debugging by looking at your JSON.

Enough with the preliminaries, let’s get started!

## Establishing a Connection

We’ll start the demo by establishing a connection between Alice’s and the Faber’s agents. We’re starting there to demonstrate that you can use agents without having a ledger. We won’t be using the Indy public ledger at all for this step. Since the agents communicate using DIDcomm messaging and connect by exchanging pairwise DIDs and DIDDocs based on the `did:peer` DID method, a public ledger is not needed.

In the Faber browser tab, execute the **`POST /connections/create-invitation`**. No data is needed to be added for this call. If successful, you should see a connection ID, an invitation, and the invitation URL. The IDs will be different on each run.

Copy the entire block of the `invitation` object, from the curly brackets `{}`, excluding the trailing comma.

Switch to the Alice browser tab and get ready to execute the **`POST /connections/receive-invitation`** section. Erase the pre-populated text and paste the invitation object from the Faber tab. When you click `Execute` a you should get back a connection ID, an invitation key, and the state of the connection, which should be `requested`.

Scroll to and execute **`GET /connections`** to see a list of the connections, and the information tracked about each connection. You should see the one connection Alice’s agent has, that it is with the Faber agent, and that its status is `active`.

You are connected! Switch to the Faber agent browser tab and run the same **`GET /connections`** endpoint to see the Faber view.  Hint - note the `connection_id`. You’ll need it later in the tutorial.

### Notes

For those familiar with the `Establish Connection` DIDcomm protocol, you might wonder why there was not an `accept-request` sent by the Faber agent. That is because in the start up parameters for the Faber agent, we used the options `--accept-invites --accept-requests`. With those set, the Faber agent accepts invites and requests automatically, without notifying the controller or waiting on an API call from the controller before proceeding. Had those not been set, the Faber controller (in this case - you), would have had to dig through the protocol state, requested a new connection be created (generating a new pairwise DID in the process) and constructed a response to the request to accept the invitation. Easily done with a controller program, but a bit of a pain when the controller is a person. Alice’s agent used similar settings to simplify the process on her side.

## Preparing to Issue a Credential

The next thing we want to do in the demo is have the Faber agent issue a credential to Alice’s agent. To this point, we have not used the Indy ledger at all. The connection and all the messaging is done with pairwise DIDs based on the `did:peer` method. Verifiable credentials must be rooted in a public DID ledger to enable the presentation of proofs.

Before the Faber agent can issue a credential, it must register a DID on the Indy public ledger, publish a schema, and create a credential definition. In the “real world”, the Faber agent would do this before connecting with any other agents, but we’ll do those steps now, Of course in the “real world”, we don’t have controllers that are people running agents using an OpenAPI user interface.

Note that since we are using the handy "./run_demo faber" (and "./run_demo alice") scripts to start up our agents, the Faber version of the script has already:

1. Registered a public DID and stored it on the ledger
2. Created a schema and registered it on the ledger
3. Created a credential definition and registered it on the ledger

The schema and credential definition can also be created through this swagger interface.

You can confirm the schema and credential definition were published by going back to the Indy ledger browser tab.  You can view the `Domain` page, refresh, scroll to the bottom and you should see transactions for the new schema and credential definition. 

### Notes

OK, we have the one time setup work for issuing a credential complete. We can now issue 1 or a million credentials without having to do those steps again. Astute readers might note that we did not setup a revocation registry, so we cannot revoke the credentials we issue with that credential definition. You can’t have everything (and we’re still working on enabling that).

## Issuing a Credential

Issuing a credential from the Faber agent to Alice’s agent is easy. In the Faber browser tab, scroll down to the **`POST /credential_exchange/send`** and get ready to (but don’t yet) execute the request. Before execution, you need to find some other data to complete the JSON. 

First, scroll back up to the **`GET /connections`** API endpoint and execute it. From the result, find the the `connection_id` and copy the value. Go back to the `/credential_exchange/send` section and paste it as the value for the `connection_id`

Next, you need to find the `credential_defintion_id` - you can look this up in the ledger browser (it is called the `Transaction ID`).In the Domains screen, scroll down and find the transaction corresponding to your credential definition.  Copy the contents of the `Transaction ID` and paste this into the value for the `credential_defintion_id`.

Finally, for the credential values, put the following between the curly brackets:

```
"name": "Alice Smith", "date": "2018-05-28", "degree": "Maths", "age": "24"
```

Ok, finally, you are ready to click `Execute`. The request should work, but if it doesn’t - check your JSON! Did you get all the quotes and commas right?

To confirm the issuance worked, scroll up to the top of the credential_exchange section and excute the **`GET /credential_exchange`** endpoint. You should see a lot of information about the exchange, including the state - `issued`.

Let’s look at it from Alice’s side. Switch to the Alice’s agent browser tab, find the `Credentials` section and within that, execute the **`GET /credentials`** endpoint. There should be a list of credentials held by Alice, with just a single entry, the credential issued from the Faber agent.

You’ve done it, issued a credential!  W00t!

### Notes

Those that know something about the Indy process for issuing a credential and the DIDcomm `Issue Credential` protocol know that there a multiple steps to issuing credentials, a back and forth between the Issuer and the Holder to (at least) offer, request and issue the credential. All of those messages happened, but the two agents took care of those details rather than bothering the controller (you, in this case) with managing the back and forth.

* On the Faber agent side, this is because we used the **`POST /credential_exchange/send`** administrative message, which handles the back and forth for the issuer automatically. We could have used the other `/credential_exchange/` endpoint to allow the controller to handle each step of the protocol.
* On Alice's agent side, this is because in the startup options for the agent, we used the `--auto-respond-credential-offer` parameter.

### Bonus Points

If you would like to manually perform all of the issuance steps on the Faber agent side, use a sequence of the other `/credential_exchange/` messages. Use the **`GET /credential_exchange`** to both check the credential exchange state as you progress through the protocol and to find some of the data you’ll need in executing the sequence of requests. If you want to run both the Faber and Alice sides in sequence, you’ll have to rerun the tutorial with Alice’s agent started without the `--auto-respond-credential-offer` parameter set.

## Requesting/Presenting a Proof

Alice now has her Faber credential. Let’s have the Faber agent send a request for a presentation (a proof) using that credential. This should be pretty easy for you at this point.

From the Faber browser tab, get ready to execute the **`POST /presentation_exchange/send_request`** endpoint. Replace the pre-populated text with the following. In doing so, use the techniques we used in issuing the credential to replace the `string` values for each instance of `cred_def_id` (there are three) and `connection_id`.

``` JSONC
{
  "requested_predicates": [
    {
      "name": "age",
      "p_type": ">=",
      "restrictions": [
        {"cred_def_id" : "string"}
      ],
      "p_value":  18
    }
  ],
  "requested_attributes": [
    {
      "name": "name",
      "restrictions": [
        {"cred_def_id" : "string"}
      ]
    },
    {
      "name": "degree",
      "restrictions": [
        {"cred_def_id" : "string"}
      ]
    }
  ],
  "name": "Proof of Education",
  "version": "1.0",
  "connection_id": "string"
}
```

Notice that the proof request is using a predicate to check if Alice is older than 18 without asking for her age. (Not sure what this has to do with her education level!) Click `Execute` and cross your fingers. If the request fails check your JSON!

Note that in the response, the state is `request_sent`. That is because when the HTTP response was generated (immediately after sending the request), Alice’s agent had not yet responded to the request. We’ll have to do another request to verify the presentation worked. Copy the value of the `presentation_exchange_id` field from the response and use it in executing the **`GET /presentation_exchange/{id}`** endpoint. That should return a result showing a status of `verified`. Proof positive!

### Notes

As with the issue credential process, the agents handled some of the presentation steps without bothering the controller.  In this case, Alice’s agent processed the presentation request automatically because it was started with the `--auto-respond-presentation-request` parameter set, and her wallet contained exactly one credential that satisfied the presentation-request from the Faber agent. Similarly, the Faber agent was started with the `--auto-verify-presentation` parameter and so on receipt of the presentation, it verified the presentation and updated the status accordingly.

## Conclusion

That’s the OpenAPI-based tutorial. Feel free to play with the API and learn how it works. More importantly, as you implement a controller, use the OpenAPI user interface to test out the calls you will be using as you go.

<!-- Docs to Markdown version 1.0β17 -->
