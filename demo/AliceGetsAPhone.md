# Alice Gets a Mobile Agent! <!-- omit in toc -->

In this demo, we'll again use our familiar Faber ACA-Py agent to issue credentials to Alice, but this time Alice will use a mobile wallet. To do this we need to run the Faber agent on a publicly accessible port (we'll use Play With Docker), and Alice will need a compatible mobile wallet. We'll provide pointers to where you can get them. As well, we'll also show how you can run through this sequence with credential revocation activated, so you can see how the mobile wallets handle that.

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

To get started with this demo using a browser, go to [Play With Docker](https://labs.play-with-docker.com/), start a terminal session. Don't know about Play with Docker? Check [this out](https://github.com/cloudcompass/ToIPLabs/blob/master/docs/LFS173x/RunningLabs.md#running-on-play-with-docker) to learn more. Once in your terminal session, use git to get this repository cloned on the instance.

```bash
git clone https://github.com/hyperledger/aries-cloudagent-python
cd aries-cloudagent-python/demo

```

Of course for this, you need to have a mobile agent. To find, install and setup a compatible mobile agent, follow the instructions [here](https://github.com/bcgov/identity-kit-poc/blob/master/docs/GettingApp.md).

### Running Locally in Docker

Unlike the ACA-Py to ACA-Py Alice/Faber demos we've run in the past, the ACA-Py to Mobile Alice scenario has an extra requirement&mdash;the ACA-Py inbound agent-to-agent transport must be publicly accessible. This is a given with Play With Docker, but trickier to do when you are running on your local machine. It can be done with something like ngrok, but we're leaving that as an exercise for the user.  If you do get it working and have instructions, please drop us a note or make a PR against this document.

### Testing with Revocation

Want to run this with revocation active? It's an option! Throughout the process we'll call out differences if you want to use revocation. Note that to use revocation with these instructions, you need a pretty good understanding of GitHub, so be warned. If this is your first run through this demo, we recommend skipping revocation and trying it on a subsequent run through. Jump down to here if you **aren't** going to use revocation.

Still here? There are some extra things you need to do to run with revocation enabled. If you are not familiar with how revocation is currently implemented in Hyperledger Indy, [this article](https://github.com/hyperledger/indy-hipe/tree/master/text/0011-cred-revocation) provides a good background on the technique. A challenge with revocation as it is currently implemented in Hyperledger Indy is the need for the prover (the agent creating the proof) to download tails files associated with the credentials it holds. Further, when using a mobile agent, mobile OSes require that all HTTP requests go over HTTPS, which Play with Docker doesn't support. So for this exercise, we're going to create our own "tails server" on the fly using GitHub.

#### Setting up a Public GitHub Tails Server

There are a number of ways to get the tails file posted on an HTTPS web service.  We're going to use GitHub. If you ideas for other/easier ways to do this, please let us us know.

We're going to use GitHub by having you create a `tails-files` repo in your personal GitHub account. We're assuming that you have your own GitHub account and repo, and that you can push updates to it. Do **NOT** do this from your Play with Docker terminal session as your GitHub credentials are not available in that environment and you should **NOT** make them available.

1. Create your tails server by creating a public github repository called `tails-files` in your personal GitHub account.

<details>
    <summary>Click here to view screenshot (github.com)</summary>
    <img src="./collateral/revocation-1-github-repo.png" alt="Github repo">
</details>

2. On your **local machine** where you have a git/github setup, open a terminal session and clone the repo to your local file system. To clone the repo, do the following, **replacing** `# NAME` with your own GitHub id:

> NOTE: Do not use Play With Docker for this because you must **NEVER** enter your credentials into a Play With Docker terminal session.
>

```bash
git clone https://github.com/# NAME/tails-files.git
cd tails-files

```

You will get an error if you forget to replace `# NAME` with your GitHub account name.

Keep this terminal session open, as we'll use it later to retrieve the tails files from Play With Docker and commit them to GitHub.

That's enough for getting started with revocation. On with the instructions!

## Run `faber` With Extra Parameters

The first step is to start the ACA-Py Faber agent. This is done differently if you are using revocation or not.

If you are not using revocation, use this command:

```bash
LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --events
```

If you are running and including revocation, use this command, replacing `# NAME` with the GitHub account in which you created the tails-file repo:

```bash
PUBLIC_TAILS_URL=https://github.com/# NAME/tails-files/raw/master TAILS_FILE_COUNT=10 LEDGER_URL=http://test.bcovrin.vonx.io ./run_demo faber --events --revocation
```

If this generated an error, check if you replaced `# NAME` with that of your GitHub account.

The `Preparing agent image...` step on the first run takes a bit of time, so while we wait, let's look at the details of the commands. Running Faber is similar to the instructions in the [Aries OpenAPI Demo](./AriesOpenAPIDemo.md) "Play with Docker" section, except:

- We are using the BCovrin Test network because that is a network that the mobile agents can be configured to use.
- We are running in "auto" mode, so we will no manual acknowledgements.
- Play with Docker exposes the Agent's' port (in this case port 8021 of the container) on a public URL that the mobile app can access.
- The revocation related changes:
  - The `PUBLIC_TAILS_URL` environment variable is the address of your tails server (must be `https`).
  - The `TAILS_FILE_COUNT` environment variable is the size of the tails file that ACA-Py will create per revocation registry.
  - The `--revocation` parameter to the `./run-demo` script activates the ACA-Py revocation issuance.

<details>
    <summary>Click here to view screenshot of th revocation registry on the ledger</summary>
    <img src="./collateral/revocation-2-ledger.png" alt="Ledger">
</details>

### Revocation Only: Copy the Tails File to GitHub

Skip this step if you are not using revocation. Jump ahead to [here](#copy-the-faber-invitation).

As the agent starts up, the tails file is published by the Faber agent itself to a local, non-HTTPS location. Before going further, you need to manually copy the file to github to make it available via https. Follow these steps to do that:

1. Scroll back in the terminal looking for something like the following in the logs:

```
Revocation Registry ID: EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2
Revocation Registry Tails File Admin URL: http://127.0.0.1:8021/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
Revocation Registry Tails File URL: https://github.com/ianco/tails-files/raw/master/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
================
mkdir -p revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/
curl -X GET "http://127.0.0.1:8021/revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file" --output revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file.bin
base64 revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file.bin >revocation/registry/EiqZU8H9QiFchygR5r3FhJ:4:EiqZU8H9QiFchygR5r3FhJ:3:CL:4420:default:CL_ACCUM:b32580f5-ed8c-4e55-a4e6-8da8c02634b2/tails-file
================
```

There are three terminal commands that you will run in your **local system** terminal session. The commands are the ones in between the "================" markers that you will run in sequence. Read about all three commands before copying/pasting/running them, as the second command may need to be altered slightly and the third skipped.

1. Go to your local system terminal session and make sure you are in the root folder of the clone of the `tails-file` repo you created.
   
2. Run the first one to (`mkdir...`) create the tails-file folder in your local github repo clone.

2. If the mobile agent you have expects the file to be base64-encoded:
   1. Copy, paste and run the second (`curl...`) and third (`base64...`) commands as is.

3. If the mobile agent you have expects the file to be as generated by the Indy SDK:
   1. Copy, paste and then edit the second (`curl...`) command and **remove the ".bin" at the end of the command** before running.
   2. Don't execute the third command (`base64...`) at all.

4. Add, commit and push the file from your local system to GitHub by running the following steps:

```bash
git add .
git commit -s -m "New tails file"
git push

```

That's it!  You are now serving your tails file on a secure https connection. There's got to be an easier way...

## Copy the Faber Invitation

When the Faber agent starts up it automatically creates an invitation.  We will copy the "url" format of the invitation for the next step.  Copy all the text between the quotes (do not include the quotes) - the copied text should be a properly formatted URL.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/S-0-invitation-1.png" alt="Select Invitation URL">
</details>

## Create a QR Code from the Invitation

To get the invitation to the agent, we need to convert the URL into a QR code that your mobile agent will read. Normally, the UI for the Faber agent would do this, but since we are just using the command line, we will use an online QR Code generator for that.

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

If you have enabled revocation, you can try revoking the credential pending publication (`faber` options `4` and `5`). For the revocation step, You will need the revocation registry identifier and the credential revocation identifier (with is 1 for the first credential you issues), as the Faber agent logged them to the console at credential issue.

Once that is done, try sending another proof request and see what happens! Experiment with immediate and pending publication.

<details>
    <summary>Click here to view screenshot</summary>
    <img src="./collateral/revocation-3-console.png" alt="Revocation">
</details>

## Conclusion

That’s the Faber-Mobile Alice demo. Feel free to play with the Swagger API and experiment further and figure out what an instance of a controller has to do to make things work.

<!-- Docs to Markdown version 1.0β17 -->
