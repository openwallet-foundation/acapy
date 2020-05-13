# Alice Gets a Mobile Agent! <!-- omit in toc -->

In this demo, we'll again use our familiar Faber ACA-Py agent to issue credentials to Alice, but this time Alice will use a mobile wallet. To do this we need to run the Faber agent on a publicly accessible port, and Alice will need a compatible mobile wallet. We'll provide pointers to where you can get them. This demo also introduces revocation of credentials.

# Contents <!-- omit in toc -->

- [Getting Started](#getting-started)
  - [Running Locally in Docker](#running-locally-in-docker)
  - [Testing with Revocation](#testing-with-revocation)
    - [Setting up a Public GitHub Tails Server](#setting-up-a-public-github-tails-server)
- [Run `faber` With Extra Parameters](#run-faber-with-extra-parameters)
  - [Revocation Only: Copy the Tails File to GitHub](#revocation-only-copy-the-tails-file-to-github)
- [Copy the Faber Invitation](#copy-the-faber-invitation)
- [Create a QR Code from the Invitation](#create-a-qr-code-from-the-invitation)
- [Accept the Invitation](#accept-the-invitation)
- [Issue a Credential](#issue-a-credential)
  - [Accept the Credential](#accept-the-credential)
- [Issue a Presentation Request](#issue-a-presentation-request)
- [Present the Proof](#present-the-proof)
- [Review the Proof](#review-the-proof)
- [Revoke the Credential and Send Another Proof Request](#revoke-the-credential-and-send-another-proof-request)
- [Conclusion](#conclusion)

## Getting Started

This demo will be run on your local machine and demonstrate credential exchange and proof exchange as well as revocation with a mobile agent.

If you are not familiar with how revocation is currently implemented in Hyperledger Indy, [this article](https://github.com/hyperledger/indy-hipe/tree/master/text/0011-cred-revocation) provides a good background on the technique. A challenge with revocation as it is currently implemented in Hyperledger Indy is the need for the prover (the agent creating the proof) to download tails files associated with the credentials it holds.

### Get a mobile agent

Of course for this, you need to have a mobile agent. To find, install and setup a compatible mobile agent, follow the instructions [here](https://github.com/bcgov/identity-kit-poc/blob/master/docs/GettingApp.md).

### Run an instance of von-tails-server in docker

For revocation to function, we need another component running that is used to store what are called tails files. In a project directory, run:

```bash
git clone git@github.com:bcgov/von-tails-server.git
cd von-tails-server/docker
./manage build && ./manage start GENESIS_URL=http://test.bcovrin.vonx.io/genesis
```

This will run the required components for the tails server to function and make a tails server available on port 6543.

### Expose services publicly using ngrok

Since the mobile agent will need some way to communicate with the agent running on your local machine in docker, we will need to create a publicly accesible url for some services on your machine. The easiest way to do this is with [ngrok](https://ngrok.com/). Once ngrok is installed, create 2 tunnels to your local machine:

```bash
ngrok http 8020
```

```bash
ngrok http 6543
```

You will see something like this for each process:

```
Forwarding                    http://abc123.ngrok.io -> http://localhost:8020
Forwarding                    https://abc123.ngrok.io -> http://localhost:8020
```

```
Forwarding                    http://def456.ngrok.io -> http://localhost:6543
Forwarding                    https://def456.ngrok.io -> http://localhost:6543
```


This creates public urls for ports 8020 and 6543 on your local machine. Keep those 2 processes running as we'll come back to them in a moment.


### Running Locally in Docker

Then, navigate to [The demo direcory](/demo) and run `PUBLIC_TAILS_URL=https://def456.ngrok.io LEDGER_URL=http://test.bcovrin.vonx.io ADMIN_ENDPOINT=https://abc123.ngrok.io ./run_demo faber --revocation --events`

You _must_ use the https urls. And make sure the urls are mapped correctly: `PUBLIC_TAILS_URL` should point to the url mapped to port `6534` and `ADMIN_ENDPOINT` to `8020`.

The `Preparing agent image...` step on the first run takes a bit of time, so while we wait, let's look at the details of the commands. Running Faber is similar to the instructions in the [Aries OpenAPI Demo](./AriesOpenAPIDemo.md) "Play with Docker" section, except:

- We are using the BCovrin Test network because that is a network that the mobile agents can be configured to use.
- We are running in "auto" mode, so we will make no manual acknowledgements.
- The revocation related changes:
  - The `PUBLIC_TAILS_URL` environment variable is the address of your tails server (must be `https`).
  - The `--revocation` parameter to the `./run-demo` script activates the ACA-Py revocation issuance.
  - The `ADMIN_ENDPOINT` variable instructs the agent to form its invitation url using this public provided endpoint

As part of its startup process, the agent will publish a revocation registry to the ledger.

<details>
    <summary>Click here to view screenshot of the revocation registry on the ledger</summary>
    <img src="./collateral/revocation-2-ledger.png" alt="Ledger">
</details>

## Accept the Invitation

When the Faber agent starts up it automatically creates an invitation and generates a QR code on the screen. On your mobile app, select "SCAN CODE" (or equivalent) and point your camera at the generated QR code.  The mobile agent should automatically capture the code and ask you to confirm the connection. Confirm it.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-1.jpg" alt="Accept Invitation">
</details>

The mobile agent will give you feedback on the connection process, something like "A connection was added to your wallet".

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-2.jpg" alt="Add Connection to Wallet">
</details>
<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-1-connect-3.jpg" alt="Add Connection to Wallet">
</details>

Switch your browser back to Play with Docker. You should see that the connection has been established, and there is a prompt for what actions you want to take, e.g. "Issue Credential", "Send Proof Request" and so on.

## Issue a Credential

We will use the Faber console to issue a credential. This could be done using the Swagger API as we have done in the connection process. We'll leave that as an exercise to the user.

In the Faber console, select option `1` to send a credential to the mobile agent.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-3-credential-0.png" alt="Issue Credential">
</details>

The Faber agent outputs details to the console; e.g.,

```text
Faber      | Credential: state = credential_issued, credential_exchange_id = bb9bf750-905f-444f-b8aa-42c3a51d9464
Faber      | Revocation registry id: Jt7PhrEc2rYuS4iVcREfoA:4:Jt7PhrEc2rYuS4iVcREfoA:3:CL:44:default:CL_ACCUM:55a13dff-c104-45b5-b633-d3fd1ac43b9a
Faber      | Credential revocation id: 1
Faber      | Credential: state = credential_acked, credential_exchange_id = bb9bf750-905f-444f-b8aa-42c3a51d9464
```

The revocation registry id and credential revocation id only appear if revocation is active. If you are doing revocation, you to need the `Revocation registry id` later, so we recommend that you copy it it now and paste it into a text file or someplace that you can access later. If you don't write it down, you can get the Id from the Admin API using the **`GET /revocation/active-registry/{cred_def_id}`** endpoint, and passing in the credential definition Id (which you can get from the **`GET /credential-definitions/created`** endpoint).

### Accept the Credential

The credential offer should automatically show up in the mobile agent. Accept the offered credential following the instructions provided by the mobile agent. That will look something like this:

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

We will use the Faber console to ask mobile agent for a proof. This could be done using the Swagger API, but we'll leave that as an exercise to the user.

In the Faber console, select option `2` to send a proof request to the mobile agent.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-0.png" alt="Request Proof">
</details>

## Present the Proof

The presentation (proof) request should automatically show up in the mobile agent. Follow the instructions provided by the mobile agent to prepare and send the proof back to Faber. That will look something like this:

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

If the mobile agent is able to successfully prepare and send the proof, you can go back to the Play with Docker terminal to see the status of the proof.

The process should "just work" for the non-revocation use case. If you are using revocation, your results may vary. As of writing this, we get failures on the wallet side with some mobile wallets, and on the Faber side with others (an error in the Indy SDK). As the results improve, we'll update this. Please let us know through GitHub issues if you have any problems running this.

## Review the Proof

In the Faber console window, the proof should be received as validated.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-4-proof-4.png" alt="Proof Validation">
</details>

## Revoke the Credential and Send Another Proof Request

If you have enabled revocation, you can try revoking the credential pending publication (`faber` options `4` and `5`). For the revocation step, You will need the revocation registry identifier and the credential revocation identifier (which is 1 for the first credential you issues), as the Faber agent logged them to the console at credential issue.

Once that is done, try sending another proof request and see what happens! Experiment with immediate and pending publication.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/revocation-3-console.png" alt="Revocation">
</details>

## Conclusion

That’s the Faber-Mobile Alice demo. Feel free to play with the Swagger API and experiment further and figure out what an instance of a controller has to do to make things work.

<!-- Docs to Markdown version 1.0β17 -->
