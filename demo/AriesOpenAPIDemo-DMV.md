<!----- Conversion time: 3.631 seconds.

Source doc: https://docs.google.com/a/cloudcompass.ca/open?id=12N1KDm1l4Az6bSOJ3DVnBs4HC3_TWz9VpIQ6WTEeykw

----->

# Aries OpenAPI Demo <!-- omit in toc -->

This demo is for developers comfortable with playing around with APIs using the OpenAPI (Swagger) user interface and JSON. The controller for each of the two agent instances in the demo is you. You drive the API exposed by the agent instances to respond to events received by each agent. The demo covers two agents, Alice and one representing the Government Driver’s Licence program. The two agents connect, and then the Government’s Department of Motor Vehicles (DMV) agent issues a Driver Licence credential to Alice, and then asks Alice to prove she possesses the credential. Who knows why the DMV Agent needs to get the proof, but it lets us show off more protocols.

# Table of Contents <!-- omit in toc -->

- [Prerequisites](#Prerequisites)
- [Starting Up](#Starting-Up)
  - [Start the VON Network](#Start-the-VON-Network)
  - [Running the DMV Agent](#Running-the-DMV-Agent)
  - [Running Alice’s Agent](#Running-Alices-Agent)
  - [Restarting the Demo](#Restarting-the-Demo)
  - [Running the Demo Steps](#Running-the-Demo-Steps)
- [Establishing a Connection](#Establishing-a-Connection)
  - [Notes](#Notes)
- [Preparing to Issue a Credential](#Preparing-to-Issue-a-Credential)
  - [Register the DMV DID](#Register-the-DMV-DID)
  - [Publish the Schema](#Publish-the-Schema)
  - [Publishing a Credential Definition](#Publishing-a-Credential-Definition)
  - [Notes](#Notes-1)
- [Issuing a Credential](#Issuing-a-Credential)
  - [Notes](#Notes-2)
  - [Bonus Points](#Bonus-Points)
- [Requesting/Presenting a Proof](#RequestingPresenting-a-Proof)
  - [Notes](#Notes-3)
- [Conclusion](#Conclusion)

## Prerequisites

To run the demo, you must have a system capable of running docker to run containers, and terminal windows running bash. On Windows systems, we highly recommend using git-bash, the Windows Subsystem for Linux (WSL) or a comparable facility. The demo will not work using PowerShell.

You can also run the agents using Python on your native system, but docker development is sooo much nicer.

Before beginning, clone, or fork and clone this repo and the [von-network](https://github.com/bcgov/von-network) repo.

## Starting Up

To begin the demo, open up three terminal windows, one for each agent - one to run a local Indy network (using the VON network) and one each for the DMV’s Agent and Alice’s Agent. You’ll also open up three browser tabs, one to allow browsing the Indy network ledger, and one for the OpenAPI user interface for each of the agents.

### Start the VON Network

In one of the terminal windows, follow the [Running the Network Locally](https://github.com/bcgov/von-network#running-the-network-locally) instructions to start (but don’t stop) a local four-node Indy network. In one of the browser tabs, navigate to [http://localhost:9000](http://localhost:9000) to see the ledger browser user interface and to verify the Indy network is running.

> NOTE: The use of localhost for the Web interfaces is assumed in this tutorial. If your docker setup is atypical, you may use a different address for your docker host.

### Running the DMV Agent

To start the DMV agent, open up a second terminal window and in it change directory to the root of your clone of this repo and execute the following command:

```bash
PORTS="5000:5000 10000:10000" ./scripts/run_docker start -it http 0.0.0.0 10000 -ot http --admin 0.0.0.0 5000 -e http://`docker run --net=host codenvy/che-ip`:10000 --genesis-url http://`docker run --net=host codenvy/che-ip`:9000/genesis --seed 00000000000000000000000000000000 --admin-insecure-mode --auto-ping-connection --auto-accept-invites --auto-accept-requests --auto-respond-credential-request --auto-verify-presentation --wallet-type indy --label "DMV Agent"
```

If all goes well, the agent will show a message indicating it is running. Use the second of the browser tabs to navigate to [http://localhost:5000](http://localhost:5000). You should see an OpenAPI user interface with a (long-ish) list of API endpoints. These are the endpoints exposed by the DMV Agent.

The `run_docker` script provides a lot of options for configuring your agent. We’ll cover the meaning of some of those options as we go. One thing you may find odd right off is this - `docker run --net=host codenvy/che-ip`. It is an inline command that invokes docker to run a container that returns the IP of the Docker Host. It’s the most portable way we know to get that information for docker running on MacOS, Windows or Linux.

### Running Alice’s Agent

To start Alice’s agent, open up a third terminal window and in it change directory to the root of your clone of this repo and execute the following command:

``` bash
PORTS="5001:5001 10001:10001" ./scripts/run_docker start -it http 0.0.0.0 10001 -ot http --admin 0.0.0.0 5001 -e http://`docker run --net=host codenvy/che-ip`:10001 --genesis-url http://`docker run --net=host codenvy/che-ip`:9000/genesis --seed 00000000000000000000000000000001 --admin-insecure-mode --auto-ping-connection --auto-accept-invites --auto-accept-requests --auto-respond-credential-offer --auto-respond-presentation-request --auto-store-credential --wallet-type indy --label "Alice Agent"
```

If all goes well, the agent will show a message indicating it is running. Use the third tab to navigate to [http://localhost:5001](http://localhost:5001). Again, you should see an OpenAPI user interface with a list of API endpoints, this time the endpoints for Alice’s agent.

### Restarting the Demo

When you are done, or to stop the demo so you can restart it, carry out the following steps:

1. in the DMV and Alice agent terminal windows, hit Ctrl-C to terminate the agents;
2. in the `von-network` terminal window, hit Ctrl-C to stop the logging, and then run the command `./manage down` to both stop the network and remove the data on the ledger. 

### Running the Demo Steps

The demo is run entirely in the Browser tabs - DMV ([http://localhost:5000](http://localhost:5000)), Alice ([http://localhost:5001](http://localhost:5001)) and the Indy public ledger ([http://localhost:9000](http://localhost:9000)). The agent terminal windows will only show messages if an error occurs in using the REST API. The Indy public ledger window will display a log of messages from the four nodes of the Indy network. In the instructions that follow, we’ll let you know if you need to be in the DMV, Alice or Indy browser tab. We’ll leave it to you to track which is which.

Using the OpenAPI user interface is pretty simple. In the steps below, we’ll indicate what API endpoint you need use, such as **`POST /connections/create-invitation`**. That means you must:

1. scroll to and find that endpoint;
2. click on the endpoint name to expand its section of the UI;
3. click on the `Try it out` button.
4. fill in any data necessary to run the command.
5. click `Execute`
6. check the response to see if the request worked.

So, the mechanical steps are easy. It’s fourth step from the list above that can be tricky. Supplying the right data and, where JSON is involved, getting the syntax correct - braces and quotes. When steps don’t work, start your debugging by looking at your JSON.

Enough with the preliminaries, let’s get started!

## Establishing a Connection

We’ll start the demo by establishing a connection between Alice’s and the DMV’s agents. We’re starting there to demonstrate that you can use agents without having a ledger. We won’t be using the Indy public ledger at all for this step. Since the agents communicate using DIDcomm messaging and connect by exchanging pairwise DIDs and DIDDocs based on the `did:peer` DID method, a public ledger is not needed.

In the DMV browser tab, execute the **`POST /connections/create-invitation`**. No data is needed to be added for this call. If successful, you should see a connection ID, an invitation, and the invitation URL. The IDs will be different on each run.

Copy the entire block of the `invitation` object, from the curly brackets `{}`, excluding the trailing comma.

Switch to the Alice browser tab and get ready to execute the **`POST /connections/receive-invitation`** section. Erase the pre-populated text and paste the invitation object from the DMV tab. When you click `Execute` a you should get back a connection ID, an invitation key, and the state of the connection, which should be `requested`.

Scroll to and execute **`GET /connections`** to see a list of the connections, and the information tracked about each connection. You should see the one connection Alice’s agent has, that it is with the DMV agent, and that its status is `active`.

You are connected! Switch to the DMV agent browser tab and run the same **`GET /connections`** endpoint to see the DMV view.  Hint - note the `connection_id`. You’ll need it later in the tutorial.

### Notes

For those familiar with the `Establish Connection` DIDcomm protocol, you might wonder why there was not an `accept-request` sent by the DMV agent. That is because in the start up parameters for the DMV agent, we used the options `--accept-invites --accept-requests`. With those set, the DMV agent accepts invites and requests automatically, without notifying the controller or waiting on an API call from the controller before proceeding. Had those not been set, the DMV controller (in this case - you), would have had to dig through the protocol state, requested a new connection be created (generating a new pairwise DID in the process) and constructed a response to the request to accept the invitation. Easily done with a controller program, but a bit of a pain when the controller is a person. Alice’s agent used similar settings to simplify the process on her side.

## Preparing to Issue a Credential

The next thing we want to do in the demo is have the DMV agent issue a credential to Alice’s agent. To this point, we have not used the Indy ledger at all. The connection and all the messaging is done with pairwise DIDs based on the `did:peer` method. Verifiable credentials must be rooted in a public DID ledger to enable the presentation of proofs.

Before the DMV agent can issue a credential, it must register a DID on the Indy public ledger, publish a schema, and create a credential definition. In the “real world”, the DMV agent would do this before connecting with any other agents, but we’ll do those steps now, Of course in the “real world”, we don’t have controllers that are people running agents using an OpenAPI user interface.

### Register the DMV DID

To write transactions to the Indy ledger, we have to first register a DID for the DMV agent.

In the startup parameters for the DMV agent, we specified a seed for the DMV agent, so we need to use that exact string to register the DID on the ledger. We’ll use the Indy ledger browser user interface to do that:

1. On the ledger browser tab, go to the section “Authenticate a New DID”.
2. Choose the “Register from seed” option. Paste a seed of 32 zeros (00000000000000000000000000000000) into the “Wallet seed” text area. That matches the seed parameter we used in starting the DMV agent.
    1. Note: If you chose the Register from DID option, would need both DID and Verkey which is annoying, so just use the seed option.
3. Click `Register DID`. If successful, should see the following:

**Identity successfully registered:**
```
Seed: 00000000000000000000000000000000
DID: 4QxzWk3ajdnEA37NdNU5Kt
Verkey: 2ru5PcgeQzxF7QZYwQgDkG2K13PRqyigVw99zMYg8eML
```

### Publish the Schema

To publish that schema, go to the DMV browser and get ready to execute the **`POST /schemas`** endpoint. Fill in the text box with the following JSON that defines the schema we’ll use:

``` JSONC
{
  "schema_name": "drivers-licence",
  "attributes": [
    "age",
    "hair_colour"
  ],
  "schema_version": "1.0"
}
```

Click `Execute`. If successful, you should see a `schema_id` in the response, most likely: `4QxzWk3ajdnEA37NdNU5Kt:2:drivers-licence:1.0`. This ID will be used for later steps in the tutorial.

To confirm the schema was published, let’s check the Indy network transactions. Go to the Indy ledger browser tab and click the **`Domain`** button, bottom left. Scroll to the bottom of the page. The last entry (#7) should be the published schema.

Schema published!

### Publishing a Credential Definition

Next up, we’ll publish the Credential Definition on the ledger.  On the DMV browser tab get ready to execute the  `POST credential-definition` endpoint. Fill in the text box with the schema ID from early (or just copy the text below) in the following JSON:

``` JSONC
{
  "schema_id": "4QxzWk3ajdnEA37NdNU5Kt:2:drivers-licence:1.0"
}
```

Click `Execute`. This step will take a bit of time as there is a lot going on in the indy-sdk to create and publish a credential definition - lots of keys being generated. Fortunately, this is not a step that happens very often, and not with real-time response requirements. You might want to open the `von-network` terminal window to see the Indy ledger nodes messaging one another. Once execution completes you should see the resulting credential definition ID, specifically: `4QxzWk3ajdnEA37NdNU5Kt:3:CL:7:default`.  

You can confirm the credential definition was published by going back to the Indy ledger browser tab, where you should still be on the `Domain` page. Refresh, scroll to the bottom and you should see transaction #8 - the new credential definition. 

### Notes

OK, we have the one time setup work for issuing a credential complete. We can now issue 1 or a million credentials without having to do those steps again. Astute readers might note that we did not setup a revocation registry, so we cannot revoke the credentials we issue with that credential definition. You can’t have everything (and we’re still working on enabling that).

## Issuing a Credential

Issuing a credential from the DMV agent to Alice’s agent is easy. In the DMV browser tab, scroll down to the **`POST /issue-credential/send`** and get ready to (but don’t yet) execute the request. Before execution, you need to find some other data to complete the JSON. 

First, scroll back up to the **`GET /connections`** API endpoint and execute it. From the result, find the the `connection_id` and copy the value. Go back to the **`POST /issue-credential/send`** section and paste it as the value for the `connection_id`.

Next, scroll down to the **`POST /credential-definitions`** section that you executed in the previous step. Expand it (if necessary) and find and copy the value of the `credential_definition_id`. You could also get it from the Indy Ledger browser tab, or from earlier in this tutorial. Go back to the **`POST /issue-credential/send`** section and paste it as the value for the `cred_def_id`.

Finally, for the credential values, put the following between the `attributes` square brackets:

```
      {
        "name": "age",
        "value": "19"
      },
      {
        "name": "hair_colour",
        "value": "brown"
      }
```

Ok, finally, you are ready to click `Execute`. The request should work, but if it doesn’t - check your JSON! Did you get all the quotes and commas right?

To confirm the issuance worked, scroll up to the top of the `v1.0 issue-credential exchange` section and execute the **`GET /issue-credential/records`** endpoint. You should see a lot of information about the exchange, including the state - `credential_acked`.

Let’s look at it from Alice’s side. Switch to the Alice’s agent browser tab, find the `credentials` section and within that, execute the **`GET /credentials`** endpoint. There should be a list of credentials held by Alice, with just a single entry, the credential issued from the DMV agent.

You’ve done it, issued a credential!  W00t!

### Notes

Those that know something about the Indy process for issuing a credential and the DIDcomm `Issue Credential` protocol know that there a multiple steps to issuing credentials, a back and forth between the Issuer and the Holder to (at least) offer, request and issue the credential. All of those messages happened, but the two agents took care of those details rather than bothering the controller (you, in this case) with managing the back and forth.

* On the DMV agent side, this is because we used the **`POST /issue-credential/send`** administrative message, which handles the back and forth for the issuer automatically. We could have used the other `/issue-credential/` endpoints to allow the controller to handle each step of the protocol.
* On Alice's agent side, this is because in the startup options for the agent, we used the `--auto-respond-credential-offer` and `--auto-store-credential` parameters.

### Bonus Points

If you would like to perform all of the issuance steps manually on the DMV agent side, use a sequence of the other `/issue-credential/` messages. Use the **`GET /issue-credential/records`** to both check the credential exchange state as you progress through the protocol and to find some of the data you’ll need in executing the sequence of requests. If you want to run both the DMV and Alice sides in sequence, you’ll have to rerun the tutorial with Alice’s agent started without the `--auto-respond-credential-offer` and `--auto-store-credential` parameters set.

## Requesting/Presenting a Proof

Alice now has her DMV credential. Let’s have the DMV agent send a request for a presentation (a proof) using that credential. This should be pretty easy for you at this point.

From the DMV browser tab, get ready to execute the **`POST /present-proof/send_request`** endpoint. Select the entire pre-populated text and replace it with the following. In doing so, use the techniques we used in issuing the credential to replace the sample values for each instance of `cred_def_id` (there are four) and `connection_id`.

``` JSONC
{
  "connection_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "proof_request": {
    "name": "bar-checks",
    "version": "1.0",
    "requested_attributes": {
      "0_hair_colour_uuid": {
        "name": "hair_colour",
        "restrictions": [
          {
            "cred_def_id": "4QxzWk3ajdnEA37NdNU5Kt:3:CL:7:default"
          }
        ]
      }
    },
    "requested_predicates": {
      "0_age_GE_uuid": {
        "name": "age",
        "p_type": ">=",
        "p_value": 18,
        "restrictions": [
          {
            "cred_def_id": "4QxzWk3ajdnEA37NdNU5Kt:3:CL:7:default"
          }
        ]
      }
    }
  }
}
```

Notice that the proof request is using a predicate to check if Alice is older than 18 without asking for her age. Click `Execute` and cross your fingers. If the request fails check your JSON!

Note that in the response, the state is `request_sent`. That is because when the HTTP response was generated (immediately after sending the request), Alice’s agent had not yet responded to the request. We’ll have to do another request to verify the presentation worked. Copy the value of the `presentation_exchange_id` field from the response and use it in executing the **`GET /present-proof/records/{pres_ex_id}`** endpoint. That should return a result showing the state as `verified` and `verified` as `true`. Proof positive!

### Notes

As with the issue credential process, the agents handled some of the presentation steps without bothering the controller.  In this case, Alice’s agent processed the presentation request automatically because it was started with the `--auto-respond-presentation-request` parameter set, and her wallet contained exactly one credential that satisfied the presentation-request from the DMV agent. Similarly, the DMV agent was started with the `--auto-verify-presentation` parameter and so on receipt of the presentation, it verified the presentation and updated the status accordingly.

## Conclusion

That’s the OpenAPI-based tutorial. Feel free to play with the API and learn how it works. More importantly, as you implement a controller, use the OpenAPI user interface to test out the calls you will be using as you go.

<!-- Docs to Markdown version 1.0β17 -->
