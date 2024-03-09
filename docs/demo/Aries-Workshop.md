# A Hyperledger Aries/AnonCreds Workshop Using Traction Sandbox

## Introduction

Welcome! This workshop contains a sequence of four labs that gets you from
nothing to issuing, receiving, holding, requesting, presenting, and verifying
AnonCreds Verifiable Credentials--no technical experience required! If you just
walk through the steps exactly as laid out, it only takes about 20 minutes to
complete the whole process. Of course, we hope you get curious, experiment, and
learn a lot more about the information provided in the labs.

To run the labs, you’ll need a Hyperledger Aries agent to be able to issue and
verify verifiable credentials. For that, we're providing your with your very own
tenant in a BC Gov "**sandbox**" deployment of an open source tool called
[Traction], a managed, production-ready, multi-tenant Aries agent built on
[Hyperledger Aries Cloud Agent Python] (ACA-Py). *Sandbox* in this context means
that you can do whatever you want with your tenant agent, but we make no
promises about the stability of the environment (but it’s pretty robust, so
chances are, things will work...), **and on the 1st and 15th of each month,
we’ll reset the entire sandbox and all your work will be gone — poof!** Keep
that in mind, as you use the Traction sandbox. We recommend you keep a notebook
at your side, tracking the important learnings you want to remember. As you
create code that uses your sandbox agent make sure you create simple-to-update
configurations so that after a reset, you can create a new tenant agent,
recreate the objects you need (each of which will have new identifiers), update
your configuration, and off you go.

The four labs in this workshop are laid out as follows:

* Lab 1: [Getting a Traction Tenant Agent and Mobile Wallet](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet)
* Lab 2: [Getting Ready To Be An Issuer](#lab-2-getting-ready-to-be-an-issuer)
* Lab 3: [Issuing Credentials to a Mobile Wallet](#lab-3-issuing-credentials-to-a-mobile-wallet)
* Lab 4: [Requesting and Sending Presentations](#lab-4-requesting-and-sending-presentations)

Once you are done the labs, there are [suggestions](#whats-next) for next steps
for developers, such as experimenting with the Traction/ACA-Py

[Traction]: https://digital.gov.bc.ca/digital-trust/technical-resources/traction/
[Hyperledger Aries Cloud Agent Python]: https://aca-py.org
[Traction Sandbox]: https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/
[BCovrin Test Ledger]: http://test.bcovrin.vonx.io/
[Traction Sandbox Workshop FAQ and Questions]: https://github.com/bcgov/traction/issues/927

Jump in!

## Lab 1: Getting a Traction Tenant Agent and Mobile Wallet

Let’s start by getting your two agents — an Aries Mobile Wallet and an Aries Issuer/Verifier agent.

### Lab 1: Steps to Follow

1. Get a compatible Aries Mobile Wallet to use with your Aries Traction tenant. There are a number to choose from.  We suggest that you use one of these:
    1. [BC Wallet](https://digital.gov.bc.ca/digital-trust/about/about-bc-wallet) from the [Government of British Columbia](https://digital.gov.bc.ca/digital-trust/)
    2. [Orbit Wallet](https://northernblock.io/orbit-edge-wallet/) from [Northern Block](https://northernblock.io/)
2. Click this [Traction Sandbox] link to go to the Sandbox login page to create your own Traction Tenant Aries agent. Once there, do the following:
    1. Click "Create Request!", fill in at least the required form fields, and click "Submit".
    2. Your new Traction Tenant's Wallet ID and Wallet Key will be displayed. **SAVE THOSE IMMEDIATELY SO THAT YOU HAVE THEM TO ACCESS YOUR TENANT**. You only get to see/save them once!
        1. You will need those each time you open your Traction Tenant agent. Putting them into a Password Manager is a great idea!
        2. We can't recover your Wallet ID and Wallet Key, so if you lose them you have to start the entire process again.
3. Go back to the [Traction Sandbox] login and this time, use your Wallet ID/Key to log in to your brand new Traction Tenant agent. You might want to bookmark the site.
4. Make your new Traction Tenant a verifiable credential issuer by:
    1. Clicking on the "User" (folder icon) menu (top right), and choosing "Profile"
    2. Clicking the “BCovrin Test” `Action` in the Endorser section.
        1. When done, you will have your own public DID (displayed on the page) that has been published on the [BCovrin Test Ledger] (can you find it?). Your DID will be used to publish other AnonCreds transactions so you can issue verifiable credentials.
5. Connect from your Traction Tenant to your mobile Wallet app by:
    1. Selecting on the left menu "Connections" and then "Invitations"
    2. Click the "Single Use Connection" button, give the connection an alias (maybe "My Wallet"), and click "Submit."
    3. Scan the resulting QR code with your initialized mobile Wallet and follow the prompts. Once you connect, type a quick "Hi!" message to the Traction Agent and you should get an automated message back.
    4. Check the Traction Tenant menu item "Connections→Connections" to see the status of your connection – it should be `active`.
    5. If anything didn't work in the sequence, here are some things to try:
       1. If the Traction Tenant connection is not `active`, it's possible that
          your wallet was not able to message back to your Traction Tenant.
          Check your wallet internet connection.
       2. We've created a [Traction Sandbox Workshop FAQ and Questions] GitHub
          issue that you can check to see if your question is already answered,
          and if not, you can add your question as comment on the issue, and
          we'll get back to you.

That's it--you should be ready to start issuing and receiving verifiable credentials.

## Lab 2: Getting Ready To Be An Issuer

::: todo
To Do: Update lab to use this schema: H7W22uhD4ueQdGaGeiCgaM:2:student id:1.0.0
:::

In this lab we will use our Traction Tenant agent to create and publish an
AnonCreds Schema object (or two), and then use that Schema to create and publish
a Credential Definition. All of the AnonCreds objects will be published on the
BCovrin (pronounced “Be Sovereign”) Test network. For those new to AnonCreds:

* A *Schema* defines the list of attributes (`claims`) in a credential. An
 issuer often publishes their own schema, but they may also use one published
 by someone else. For example, a group of universities all might use the schema
 published by the "Association of Universities and Colleges" to which they
 belong.
* A *Credential Definition* (`CredDef`) is published by the issuer, linking
 together Issuer's DID with the schema upon which the credentials will be
 issued, and containing the public key material needed to verify presentations
 of the credential. Revocation Registries are also linked to the Credential
 Definition, enabling an issuer to revoke credentials when necessary.

### Lab 2: Steps to Follow

1. Log into your [Traction Sandbox]. You did record your Wallet ID and Key, right?
    1. If not — jump back to [Lab 1](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet) to create a
       new Traction Tenant, and to a connection to your mobile Wallet.
2. Create a Schema:
    1. Click the menu item “Configuration” and then “Schema Storage”.
    2. Click “Add Schema From Ledger” and fill in the `Schema Id` with the value `H7W22uhD4ueQdGaGeiCgaM:2:student id:1.0.0`.
        1. By doing this, you (as the issuer) will be using a previously
        published schema. [Click
        here](http://test.bcovrin.vonx.io/browse/domain?page=1&query=H7W22uhD4ueQdGaGeiCgaM&txn_type=101)
        to see the schema on the ledger.
    3. To see the details about your schema, hit the Expand (`>`) link, and then
       the subsequent `>` to “View Raw Content."
3. With the schema in place, it's time to become an issuer. To do that, you have
   to create a Credential Definition. Click on the “Credential” icon in the
   “Credential Definition” column of your schema to create the Credential
   Definition (CredDef) for the Schema. The “Tag” can be any value you want — it
   is an issuer defined part of the identifier for the Credential Definition.
   Wait for the operation to complete. Click the “Refresh” button if needed to
   see the Create icon has been replaced with the identifier for your CredDef.
4. Move to the menu item "Configuration → Credential Definition Storage" to see
   the CredDef you created, If you want, expand it to view the raw data. In this
   case, the raw data does not show the actual CredDef, but rather the Traction data
   about the CredDef. You can again use the [BCovrin Test ledger] browser to
   see your new, published CredDef.

Completed all the steps? Great! Feel free to create a second Schema and Cred
Def, ideally one related to your first. That way you can try out a presentation
request that pulls data from both credentials! When you create the second
schema, use the "Create Schema" button, and add the claims you want to have in
your new type of credential.

## Lab 3: Issuing Credentials to a Mobile Wallet

In this lab we will use our Traction Tenant agent to issue instances of the
credentials we created in [Lab 2](#lab-2-getting-ready-to-be-an-issuer) to our
Mobile Wallet we downloaded in [Lab
1](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet).

### Lab 3: Steps to Follow

1. If necessary, log into your [Traction Sandbox] with your Wallet ID and Key.
2. Issue a Credential:
    1. Click the menu item “Issuance” and then “Offer a Credential”.
    2. Select the Credential Definition of the credential you want to issue.
    3. Select the Contact Name to whom you are issuing the credential—the alias of the connection you made to your mobile Wallet.
    4. Click the “Enter Credential Value” to popup a data entry form for the attributes to populate.
        1. When you enter the date values that you want to use in predicates
           (e.g., “Older than 19”), put the date into the following format:
           **`YYYYMMDD`**, e.g., **`20231001`**. You cannot use a string date
           format, such as “YYYY-MM-DD” if you want to use the attribute for
           predicate checking -- the value must be an integer.
        2. We suggest you use realistic dates for Date of Birth (DOB) (e.g., 20-ish
           years in the past) and expiry (e.g., 3 years in the future) to make
           using them in predicates easier.
    5. Click “Save” when you are finished entering the attributes and review the
       information you have entered.
    6. When you are ready, click “Send Offer” to initiate the issuance of the
       credential.
3. Receive the Credential:
    1. Open up your mobile Wallet and look for a notification about the credential offer. Where that appears may vary based on the Wallet you are using.
    2. Review the offer and then click the “Accept” button.
    3. Your new credential should be saved to your wallet.
4. Review the Issuance Data:
    1. Back in your Traction Tenant, refresh the list to see the updates status of the issuance you just completed (should be “credential_issued” or “credential_acked”, depending on the Wallet you are using).
    2. Expand the issuance and again to “View Raw Content.” to see the data that was exchanged between the Traction Issuer and the Wallet.
5. If you want, repeat the process for other credentials types your Traction Tenant is capable of issuing.

That’s it! Pretty easy, eh? Of course, in a real issuer, the data would (very,
very) likely not be hand-entered, but instead come from a backend system.
Traction has an HTTP API (protected by the same Wallet ID and Key) that can be
used from an application, to do things like this automatically. The Traction API
embeds the ACA-Py API, so everything you can do in “plain ACA-Py” can also be
done in Traction.

## Lab 4: Requesting and Sending Presentations

In this lab we will use our Traction Tenant agent as a verifier, requesting
presentations, and your mobile Wallet as the holder responding with
presentations that satisfy the requests. The user interface is a little rougher
for this lab (you’ll be dealing with JSON), but it should still be easy enough
to do.

### Lab 4: Steps to Follow

1. If necessary, log into your [Traction Sandbox] with your Wallet ID and Key.
2. Create and send a presentation request:
    1. Click the menu item “Verification” and then the button “Create Presentation Request”.
    2. Select the Connection to whom you are sending the request—the alias of the connection you made to your mobile Wallet.
    3. Update the example Presentation Request to match the credential that you want to request. Keep it simple for your first request—it’s easy to iterate in Traction to make your request more complicated. If you used the schema we suggested in Lab 1, just use the default presentation request. It should just work! If not, start from it, and:
         1. Update the value of “schema_name” to the name(s) of the schema for the credential(s) you issued.
         2. Update the group name(s) to something that makes sense for your credential(s) and make sure the attributes listed match your credential(s).
         3. Update (or perhaps remove) the “request_predicates” JSON item, if it is not applicable to your credential.
    4. Update the optional fields (“Auto Verify” and “Optional Comment”) as you see fit. The “Optional Comment” goes into the list of Verifications so you can keep track of the different presentation requests you create.
    5. Click “Submit” when your presentation request is ready.
3. Respond to the Presentation Request:
    1. Open up your mobile Wallet and look for a notification about receiving a presentation request. Where that appears may vary based on the Wallet you are using.
    2. Review the information you are being asked to share, and then click the “Share” button to send the presentation.
4. Review the Presentation Request Result:
    1. Back in your Traction Tenant, refresh the Verifications list to see the updated status of the presentation request you just completed. It should be something positive, like “presentation_received” if all went well. It may be different depending on the Wallet you are using.
    2. If you want, expand the presentation request and “View Raw Content.” to see the presentation request, and presentation data exchanged between the Traction Verifier and the Wallet.
5. Repeat the process, making the presentation request more complicated:
    1. From the list of presentations, use the arrow icon action to copy an existing presentation request and just re-run it, or evolve it.
    2. Ideas:
       1. Add predicates using date of birth (“older than”) and expiry (“not expired today”).
           1. The **`p_value`** should be a relevant date — e.g., 19 (or whatever) years ago today for “older than”, and today for “not expired”, both in the **`YYYYMMDD`** format (the integer form of the date).
           2. The **`p_type`** should be **`>=`** for the “older than”, and **`=<`** for “not expired”.  See the table below for the form of the expression form.
    3. Add a second credential group with a restriction for a different credential to the request, so the presentation is derived from two source credentials.

| p_value  | p_type | credential_data |
| -------- | ------ | --------------- |
| 20230527 | <=     | expiry_dateint  |
| 20030527 | >=     | dob_dateint     |

That completes this lab — although feel free to continue to play with all of the steps (setup, issuing and presenting). You should have a pretty solid handle on exactly what you can and can’t do with AnonCreds!

## What's Next

The following are a couple of things that you might want to do next--if you are
a developer. Unlike the labs you have just completed, these "next steps" are
geared towards developers, providing details about building the use of
verifiable credentials (issuing, verifying) into your own application.

Want to use [Traction] in your own environment? Feel free! It's open source, and
comes with Helm Charts for easy deployment in container-orchestrated
environments. Contributions back to the project are always welcome!

### What’s Next: The ACA-Py OpenAPI

Are you going to build an app that uses Traction or an instance of the [Aries Cloud Agent Python](https://aca-py.org/) (ACA-Py)? If so, your next step is to try out the ACA-Py OpenAPI (aka Swagger)—by hand at first, and then from your application. This is a VERY high level overview, assuming a developer is following this, and knows a bunch about Aries protocols, using HTTP APIs, and using OpenAPI interfaces.

To access and use your Tenant's OpenAPI (aka Swagger) interface:

* In your Traction Tenant, click the User icon (top right) and choose “Developer”
* Scroll to the bottom and expand the “Encoded JWT”, and click the “Copy” icon to the right to get the JWT into your clipboard.
  * By using the “copy” icon, the JWT is prefixed with “Bearer “, which is needed in the OpenAPI authorization. If you just highlight and copy the JWT, you don’t get the prefix.
* Click on “About” from the left menu and then click “Traction.”
* Click on the link with the “Swagger URL” label to open up the OpenAPI (Swagger) API.
  * The URL is just the normal [Traction Tenant API with `”api/doc”](https://traction-sandbox-tenant-proxy.apps.silver.devops.gov.bc.ca/api/doc) added to it.
* Click Authorize in the top right, click in the second box “AuthorizationHeader (apiKey)” and paste in your previously copied encoded JWT.
* Close the authorization window and try out an Endpoint. For example, scroll down to the “GET /connections” endpoint, “Try It Out” and “Execute”.  You should get back a list of the connections you have established in your Tenant.

The ACA-Py/Traction API is pretty large, but it is reasonably well organized, and you should recognize from the Traction API a lot of the items. Try some of the “GET” endpoints to see if you recognize the items.

We’re still working on a good demo for the OpenAPI from Traction, but [this one
from
ACA-Py](https://aca-py.org/main/demo/AriesOpenAPIDemo/#using-the-openapiswagger-user-interface)
is a good outline of the process. It doesn't use your Traction Tenant, but you
should get the idea about the sequence of calls to make to accomplish Aries-type
activities. For example, see if you can carry out the steps to do the [Lab
4](#lab-4-requesting-and-sending-presentations) with your mobile agent by
invoking the right sequence of OpenAPI calls.

### What's Next: Experiment With an Issuer Web App

If you are challenged to use Traction or [Aries Cloud Agent Python] to become an
issuer, you will likely be building API calls into your Line of Business web
application. To get an idea of what that will entail, we're delighted to direct
you to a very simple Web App that one of your predecessors on this same journey
created (and contributed!) to learn more about using the Traction OpenAPI in a
very simple Web App. Checkout this [Traction Issuance Demo] and try it out
yourself, with your Sandbox tenant. Once you review the code, you should have an
excellent idea of how you can add these same capabilities to your line of
business application.

[Traction Issuance Demo]: https://github.com/hyperledger/aries-acapy-controllers/tree/main/TractionIssuanceDemo
