# Aries OpenAPI Mobile Demo <!-- omit in toc -->

You can use the Faber aca-py agent to issue credentials to a mobile wallet.  To do this you need to run the Faber agent on a publicly accessible port (for example you can run the agent on Play With Docker), and you need a compatible wallet.  One available wallet is the Streetcred Identity Agent, which is available on both iOS and Android. Installation and setup instructions are available [here](https://github.com/bcgov/identity-kit-poc/blob/master/docs/GettingApp.md).

# Contents <!-- omit in toc -->

- [Getting Started](#getting-started)
- [Running in a Browser](#running-in-a-browser)
- [Running Locally in Docker](#running-locally-in-docker)
- [Testing with Revocation](#testing-with-revocation)
  - [Set up a Public GitHub Tails Server](#set-up-a-public-github-tails-server)
  - [Run `faber` With Extra Parameters](#run-faber-with-extra-parameters)
  - [Copy the Tails File to GitHub](#copy-the-tails-file-to-github)
- [Install a Mobile Agent](#install-a-mobile-agent)
- [Copy the Faber Invitation](#copy-the-faber-invitation)
- [Create a QR Code from the Invitation](#create-a-qr-code-from-the-invitation)
- [Accept the Invitation](#accept-the-invitation)
- [Accept the Mobile Agent's Connection Request](#accept-the-mobile-agents-connection-request)
- [Issue a Credential](#issue-a-credential)
  - [Accept the Credential](#accept-the-credential)
- [Issue a Presentation Request](#issue-a-presentation-request)
- [Present the Proof](#present-the-proof)
- [Review the Proof](#review-the-proof)
- [Revoke the Credential and Send Another Proof Request](#revoke-the-credential-and-send-another-proof-request)
- [Conclusion](#conclusion)

## Getting Started

This is an add-on workshop to the [Aries OpenAPI Demo](./AriesOpenAPIDemo.md) activity, which includes more background on how to use the API user interface (Swagger) and interact with an Aries agent. If aren't familiar with the Swagger UI, you might want to do that exercise first.

## Running in a Browser

To get started in a browser, go to [Play With Docker](https://labs.play-with-docker.com/), start a terminal session, and start your agent using the BCovrin Test network as follows. 

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo
LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --events
```

This is similar to the instructions in the prior "Play with Docker" section, except note that:

- We are using the BCovrin Test network (it has to use the same network as the mobile app)
- We are running in "auto" mode, so we will have to do fewer manual acknowledgements
- Play with Docker exposes the Agent's' port (in this case port 8021 of the container) on a public URL that the mobile app can access

## Running Locally in Docker

An alternative for running locally&mdash;left as an exercise for the user&mdash;is to use ngrok and then set your agent's endpoint to the ngrok url.

## Testing with Revocation

Want to run this with revocation active?  There are some extra things you need to do to run with revocation enabled:

1. Setup a public `https` repository to publish the tails files. In this example we will publish to github.
2. Run `faber` with a few extra parameters (given below).

Note that the `https` requirement is necessary because of the operating system on which the mobile wallets are running.

### Set up a Public GitHub Tails Server

There are a number of ways to get the tails file posted on an HTTPS web service.  We're going to use GitHub. If you ideas for other/easier ways to do this, please let us us know. In these instructions, we're going to use GitHub by having you create a `tails-files` repo in your personal GitHub account. We're assuming that you have your own GitHub account and repo, and that you can push updates to it.

1. Implement a tails server by creating a public github repository called `tails-files` in your personal GitHub account.

<details>
    <summary>Click here to view screenshot (github.com)</summary>
    <img src="./collateral/revocation-1-github-repo.png" alt="Github repo">
</details>

2. On your **local machine** where you have a git/github setup, open a terminal session and clone the repo in your local `/tmp` directory. To clone the repo, do the following, replacing `ianco` with your own GitHub id:

> NOTE: You can't use Play With Docker for this because you must **NEVER** enter your credentials into a Play With Docker terminal session.
> 
> NOTE: Later instructions assume you put the clone of the repo in the `/tmp/` folder on your system as specified below. If you put it elsewhere, you need to watch for that later in the instructions.

```bash
$ cd /tmp/
$ git clone https://github.com/ianco/tails-files.git
```

That's it!  You will manually copy tails files here and then commit them to github.

### Run `faber` With Extra Parameters

You have to tell `faber` (a) to enable revocation, and (b) to advertise the location of the tails files in github.

You accomplish this in Play With Docker by hitting `Ctrl-c` to stop your previous start of Faber and executing the following:

```bash
PUBLIC_TAILS_URL=https://github.com/ianco/tails-files/raw/master TAILS_FILE_COUNT=10 LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --events --revocation
```

The `--revocation` flag tells faber to enable revocation and create a revocation registry and tails file.

For `PUBLIC_TAILS_URL`, substitute `ianco` with your GitHub ID. Later, you will see this URL in the ledger transaction for the revocation registry.  If you copy & paste the `Tails file location:` url into your browser it should download the tails file.

<details>
    <summary>Click here to view screenshot (ledger)</summary>
    <img src="./collateral/revocation-2-ledger.png" alt="Ledger">
</details>

For `TAILS_FILE_COUNT`, enter the size of your tails file.  Use a small number to keep things quick!  10 or 20 is fine for this demo.

### Copy the Tails File to GitHub

As the agent starts up, the tails file is published by the agent itself to a local, non-HTTPS location. Before going further, you need to manually copy the to github to make it available via https. Follow these steps to do that:

1. Scroll back in the terminal looking for the following in the logs:

```
Revocation Registry ID: EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2
Revocation Registry Tails File Admin URL: http://127.0.0.1:8021/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
Revocation Registry Tails File URL: https://github.com/ianco/tails-files/raw/master/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
================
mkdir -p /tmp/tails-files/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/
curl -X GET "http://127.0.0.1:8021/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file" --output /tmp/tails-files/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
================
```

There are two terminal commands in between the "================" markers that you will run in sequence.

2. Run the first one `mkdir...` to create the folder in your local github repo clone:

3. Copy, paste and edit the second **before** running. You must change `http://127.0.0.1:8021/` to the public IP address of port 8021 of your Play with Docker session. To get that URL, click `8021` at the top of the screen (carefully&mdash;sometimes it moves around!) or click `Open Port`, enter `8021` when prompted. Either way, a new browser tab will open.
   
4. Update the command line and run the command. It will download the file from the agent to the git repo.

5. Commit the file from your local system by running the following steps:

```bash
cd /tmp/tails-files
git add .
git commit -m "New tails file"
git push
```

That's it!  You are now serving your tails file on a secure https connection.

> There's got to be an easier way...

## Install a Mobile Agent

To find, install and setup a compatible mobile agent, follow the instructions [here](https://github.com/bcgov/identity-kit-poc/blob/master/docs/GettingApp.md).

## Copy the Faber Invitation

When the Faber agent starts up it automatically creates an invitation.  We will copy the "url" format of the invitation for the next step.  Copy all the text between the quotes (do not include the quotes) - the copied text should be a properly formatted URL.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-0-invitation-1.png" alt="Select Invitation URL">
</details>

## Create a QR Code from the Invitation

To get the invitation to the agent, we need to convert the URl into a QR code.  Your application can do this, but for this demo we will use an online QR Code generator.

Open [https://www.the-qrcode-generator.com/](https://www.the-qrcode-generator.com/) in a new browser window, and:

- Select the "URL" option
- Paste your invitation url into the provided input field

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-0-invitation-2.png" alt="Generate QR Code">
</details>

## Accept the Invitation

On your mobile app, select "SCAN CODE" (or equivalent) and point your camera at the generated QR code.  The mobile agent should automatically capture the code and ask you to confirm the connection. Confirm it.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-1.jpg" alt="Accept Invitation">
</details>

The mobile agent will give you a message that "A connection was added to your wallet".

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-2.jpg" alt="Add Connection to Wallet">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-3.jpg" alt="Add Connection to Wallet">
</details>

## Accept the Mobile Agent's Connection Request

At this point Faber has issued an invitation, you have accepted the invitation, and asked Faber to establish a connection to your agent.  Faber must now accept this request.  You can see the Event in the Faber terminal window.  Find this event, and select and copy the "connection id".

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-2-connect-1.png" alt="Accept Connection Request">
</details>

Now, on Faber's Swagger page (if not open, at the top of the console window, click on port `8021` to open the Swagger page in a new window) scroll down to the **`POST /connections/{id}/accept-request`** endpoint, click `Try It Now`, paste the connection id and click on "Execute".

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-2-connect-2.png" alt="Accept Connection Request">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-2-connect-3.png" alt="Accept Connection Request">
</details>

Scroll to the **`GET /connections`** endpoint to check the status of the connection.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-2-connect-4.png" alt="View Connection Status">
</details>

Note - if the connection status does not update to `active`, send a `trust-ping` or `basic-message` on the connection.  This will force a handshake between the agents that should activate the connection.

## Issue a Credential

We will use the Faber console to issue a credential. This could be done using the Swagger API as we have done in the connection process. We'll leave that as an exercise to the user.

In the Faber console, select option `1` to send a credential to the mobile agent.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-3-credential-0.png" alt="Issue Credential">
</details>

The Faber agent outputs details to the console; e.g.,
```
Faber      | Credential: state = credential_issued, credential_exchange_id = bb9bf750-905f-444f-b8aa-42c3a51d9464
Faber      | Revocation registry id: Jt7PhrEc2rYuS4iVcREfoA:4:Jt7PhrEc2rYuS4iVcREfoA:3:CL:44:default:CL_ACCUM:55a13dff-c104-45b5-b633-d3fd1ac43b9a
Faber      | Credential revocation id: 1
Faber      | Credential: state = credential_acked, credential_exchange_id = bb9bf750-905f-444f-b8aa-42c3a51d9464
```
where the revocation registry id and credential revocation id only appear if revocation is active.

### Accept the Credential

The credential offer should automatically show up in the mobile agent. Accept the offered credential.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-3-credential-1.jpg" alt="Credential Offer">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-3-credential-2.jpg" alt="Credential Details">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-3-credential-3.jpg" alt="Credential Acceptance">
</details>

## Issue a Presentation Request

We will use the Faber console to ask mobile agent for a proof. This could be done using the Swagger API as we have done in the connection process. We'll leave that as an exercise to the user.

In the Faber console, select option `2` to send a proof request to the mobile agent.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-0.png" alt="Request Proof">
</details>

## Present the Proof

In the mobile agent, select the option to present the requested proof.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-1.jpg" alt="Proof Request Notice">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-2.jpg" alt="Proof Request Details">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-3.jpg" alt="Proof Presentation">
</details>

## Review the Proof

In the Faber console window, the proof should be received as validated.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-4.png" alt="Proof Validation">
</details>

## Revoke the Credential and Send Another Proof Request

If you have enabled revocation, you can try revoking the credential pending publication (`faber` options `4` and `5`). For the revocation step, You will need the revocation registry identifier and the credential revocation identifier, as the Faber agent logged them to the console at credential issue.

Once that is done, try sending another proof request and see what happens! Experiment with immediate and pending publication.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/revocation-3-console.png" alt="Revocation">
</details>

## Conclusion

That’s the OpenAPI-based tutorial. Feel free to play with the API and learn how it works. More importantly, as you implement a controller, use the OpenAPI user interface to test out the calls you will be using as you go. The list of API calls is grouped by protocol and if you are familiar with the protocols (Aries RFCs) the API call names should be pretty obvious.

One limitation of you being the controller is that you don't see the events from the agent that a controller program sees. For example, you, as Alice's agent, are not notified when Faber initiates the sending of a Credential. Some of those things show up in the terminal as messages, but others you just have to know have happened based on a successful API call.

<!-- Docs to Markdown version 1.0β17 -->
