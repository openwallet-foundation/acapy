# WebVH and AnonCreds Workshop Using Traction Sandbox

## Introduction

Welcome! This workshop will guide you through issuing, receiving, holding, requesting, presenting, and verifying AnonCreds Verifiable Credentials using the **WebVH (Web Verifiable History)** DID method.

### Workshop Structure

This workshop is divided into two parts:

#### Part 1: WebVH Basics

A hands-on sequence of labs that gets you from nothing to a working credential system. **No technical experience required!**

- Complete the basic labs in about 20 minutes
- Includes a bonus lab on credential revocation
- Learn through step-by-step instructions

#### Part 2: OpenAPI (Swagger) Integration

Learn how to programmatically interact with your Traction tenant and WebVH resources using REST APIs.

- Automate credential issuance and verification
- Requires basic knowledge of HTTP APIs
- Optional: Python or JavaScript experience helpful

### What You'll Need

To run the labs, you'll need:

1. **A mobile wallet** - A compatible mobile wallet app to receive and hold credentials. We recommend:
   - [BC Wallet](https://digital.gov.bc.ca/design/digital-trust/digital-credentials/bc-wallet/) from the Government of British Columbia
   - [PyDentity Wallet](https://github.com/openwallet-foundation-labs/PyDentity-Wallet) from OpenWallet Foundation Labs

2. **A Traction tenant** - We're providing you with your very own tenant in a BC Gov **sandbox** deployment of [Traction](https://digital.gov.bc.ca/digital-trust/technical-resources/traction/), a managed, production-ready, multi-tenant decentralized trust agent built on [ACA-Py](https://aca-py.org). You'll create this in Lab 1.

> **⚠️ Important Sandbox Notice**
>
> This is a **sandbox environment**:
>
> - You can experiment freely with your tenant agent
> - The environment is generally stable, but no guarantees are made
> - **On the 1st and 15th of each month, the entire sandbox is reset and all your work will be deleted**
>
> **Recommendations:**
>
> - Keep a notebook to track important learnings
> - Save your Wallet ID and Wallet Key securely (you'll need them to access your tenant)
> - If you create code, use simple-to-update configurations
> - After a reset, you can quickly recreate your tenant and objects

### What is WebVH?

**WebVH (Web Verifiable History)** is a DID method that enables issuers to publish AnonCreds objects (schemas, credential definitions, revocation registries) as **Attested Resources** on a web server.

Unlike traditional blockchain-based ledgers, WebVH uses HTTP-based resolution, making it easier to deploy and maintain while still providing cryptographic integrity through digital signatures.

#### Key Advantages

- **No blockchain required** - Uses standard web infrastructure
- **Cryptographic integrity** - All resources are signed with Data Integrity Proofs
- **Privacy-preserving** - Supports the same AnonCreds privacy features as blockchain-based systems
- **Easier deployment** - Can be hosted on any web server
- **Witness-based trust** - Uses witness services for attestation instead of blockchain consensus

### Workshop Labs

#### Part 1: WebVH Basics

1. [Getting a Traction Tenant Agent and Mobile Wallet](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet)
2. [Configuring WebVH and Creating a WebVH DID](#lab-2-configuring-webvh-and-creating-a-webvh-did)
3. [Creating Schemas and Credential Definitions with WebVH](#lab-3-creating-schemas-and-credential-definitions-with-webvh)
4. [Issuing Credentials to a Mobile Wallet](#lab-4-issuing-credentials-to-a-mobile-wallet)
5. [Requesting and Verifying Presentations](#lab-5-requesting-and-verifying-presentations)
6. [Revoking Credentials and Exploring Revocation Entries](#lab-5a-revoking-credentials-and-exploring-revocation-entries) *(Bonus Lab)*

#### Part 2: OpenAPI (Swagger) Integration

7. [Accessing the OpenAPI Interface](#lab-6-accessing-the-openapi-interface)
8. [Using the API to Issue Credentials Programmatically](#lab-7-using-the-api-to-issue-credentials-programmatically)
9. [Using the API to Request Presentations Programmatically](#lab-8-using-the-api-to-request-presentations-programmatically)
10. [Revoking Credentials and Exploring Revocation Entries](#lab-9-revoking-credentials-and-exploring-revocation-entries) *(Bonus Lab)*

### Next Steps

Once you complete the labs, check out the [suggestions for next steps](#whats-next) section for developers, including:

- Experimenting with the Traction/ACA-Py API
- Building your own applications
- Understanding WebVH resolution
- Exploring example web applications

### Resources

- [Traction](https://digital.gov.bc.ca/digital-trust/technical-resources/traction/) - Managed, production-ready, multi-tenant decentralized trust agent
- [ACA-Py](https://aca-py.org) - Cloud Agent Python framework
- [WebVH](https://identity.foundation/did-webvh/) - Web Verifiable History DID method specification
- [Traction Sandbox Workshop FAQ and Questions](https://github.com/bcgov/traction/issues/927) - Get help and ask questions

---

**Ready to get started?** Jump into [Lab 1](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet)!

## Lab 1: Getting a Traction Tenant Agent and Mobile Wallet

<a id="lab-1-getting-a-traction-tenant-agent-and-mobile-wallet"></a>

Let's start by getting your two agents — a Mobile Wallet and an Issuer/Verifier agent.

### Lab 1: Steps to Follow

1. Get a compatible mobile wallet to use with your Traction tenant. There are a number to choose from.  We suggest that you use one of these:
    1. [BC Wallet](https://digital.gov.bc.ca/design/digital-trust/digital-credentials/bc-wallet/) from the [Government of British Columbia](https://digital.gov.bc.ca/design/digital-trust/)
    2. [PyDentity Wallet](https://github.com/openwallet-foundation-labs/PyDentity-Wallet) from [OpenWallet Foundation Labs](https://openwallet.foundation/)
2. Click this [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) link to go to the Sandbox login page to create your own Traction Tenant agent. Once there, do the following:
    1. Click "Create Request!", fill in at least the required form fields, and click "Submit".
    2. Your new Traction Tenant's Wallet ID and Wallet Key will be displayed. **SAVE THOSE IMMEDIATELY SO THAT YOU HAVE THEM TO ACCESS YOUR TENANT**. You only get to see/save them once!
        1. You will need those each time you open your Traction Tenant agent. Putting them into a Password Manager is a great idea!
        2. We can't recover your Wallet ID and Wallet Key, so if you lose them you have to start the entire process again.
3. Go back to the [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) login and this time, use your Wallet ID/Key to log in to your brand new Traction Tenant agent. You might want to bookmark the site.
4. Connect from your Traction Tenant to your mobile Wallet app by:
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

That's it--you should be ready to start configuring WebVH and issuing verifiable credentials.

## Lab 2: Configuring WebVH and Creating a WebVH DID

<a id="lab-2-configuring-webvh-and-creating-a-webvh-did"></a>

In this lab we will configure your Traction Tenant to use WebVH as the registry
for AnonCreds objects, and create a WebVH DID that will serve as your issuer
identifier. Unlike traditional blockchain-based ledgers, WebVH uses a witness-based
attestation model where a witness service signs and attests to your DID creation
and updates.

### Lab 2: Steps to Follow

1. If necessary, log into your [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) with your Wallet ID and Key.
2. Upgrade your wallet to support AnonCreds (if needed):
    1. Click on the "User" (folder icon) menu (top right), and choose "Settings"
    2. Scroll down to the "Wallet Type" section. You should see your current wallet type displayed (e.g., `askar` or `askar-anoncreds`).
    3. If your wallet type is `askar` (not `askar-anoncreds`), you'll see an "Upgrade Wallet" button with a warning icon. **WebVH requires AnonCreds support, so you must upgrade your wallet first.**
    4. Click the "Upgrade Wallet" button. You'll see a confirmation dialog warning that this is a **non-reversible operation**. Make sure you understand this before proceeding.
    5. Confirm the upgrade. The upgrade process will run in the background. You should see a success message indicating that the upgrade has been triggered.
    6. Wait a few moments for the upgrade to complete. You may need to refresh the Settings page to see the wallet type change to `askar-anoncreds`.
    7. **Important**: If your wallet is already `askar-anoncreds`, you can skip this step and proceed directly to configuring WebVH.
3. Configure WebVH in your Traction Tenant:
    1. Click on the "User" (folder icon) menu (top right), and choose "Profile"
    2. Scroll down to the "WebVH Servers" section. You should see a table with WebVH server information.
    3. Click the "Connect" button (the user-plus icon) next to the WebVH server entry. This will configure your tenant to use WebVH as an AnonCreds registry.
    4. Wait for the configuration to complete. You should see a success message indicating that WebVH has been configured.
4. Create a WebVH DID:
    1. Navigate to the "Identifiers" menu item in the left sidebar.
    2. If you see a warning message about WebVH configuration, make sure you completed step 3 above.
    3. Click the "Create DID" button (or "Create WebVH DID" if labeled).
    4. In the dialog that appears:
        - **Server URL**: This should be pre-populated with the configured WebVH server URL (e.g., `sandbox.bcvh.vonx.io`)
        - **Namespace**: You can leave this as `default` or enter a custom namespace if you want to organize your DIDs
        - **Alias**: Enter a unique label for your identifier (e.g., `my-issuer` or `workshop-demo`)
    5. Click "Submit" to create your WebVH DID.
    6. The DID creation process will:
        - Generate a new DID with the format `did:webvh:{SCID}:{domain}:{namespace}:{identifier}`
        - Request attestation from the witness service
        - Wait for the witness to sign and attest to your DID
    7. Initially, your DID will show a status of "Pending". Once the witness completes attestation (usually within a few seconds), the status will change to "Active".
    8. Your new WebVH DID will be displayed in the Identifiers table. **Copy and save your DID** - you'll need it for the next lab!
5. Verify your WebVH DID:
    1. Once your DID status shows as "Active", you can click on it to view details.
    2. You should see your full DID string (e.g., `did:webvh:{SCID}:sandbox.bcvh.vonx.io:default:my-issuer`)
    3. This DID is now your issuer identifier and will be used when publishing AnonCreds schemas and credential definitions.
6. Resolve your WebVH DID using the Universal Resolver:
    1. The Universal Resolver is a service that can resolve DIDs from various methods, including WebVH. This allows you to verify that your DID is publicly resolvable and view its DID Document.
    2. Open your web browser and navigate to the [Universal Resolver](https://uniresolver.io/) web interface.
    3. In the input field, paste your WebVH DID (the full DID string you copied earlier).
    4. Click "Resolve" (or press Enter).
    5. The Universal Resolver will fetch and display your DID Document, which includes:
        - Your DID identifier
        - Verification methods (public keys)
        - Service endpoints
        - Other metadata
    6. **Alternative: Using the API directly**: You can also resolve your DID programmatically using the Universal Resolver API:
        ```bash
        curl -X GET \
        "https://dev.uniresolver.io/1.0/identifiers/did:webvh:{SCID}:sandbox.bcvh.vonx.io:default:my-issuer"
        ```
        Replace the DID in the URL with your actual DID. This will return the DID Document in JSON format.
    7. Verifying that your DID resolves successfully confirms that:
        - Your DID is properly published on the WebVH server
        - The witness attestation was successful
        - Other parties (including wallets) can resolve your DID to find your public keys and services

Completed all the steps? Great! You now have a WebVH DID that can be used to publish AnonCreds objects. Unlike blockchain-based DIDs, your WebVH DID is resolved via HTTP, making it easier to work with while still maintaining cryptographic integrity. The Universal Resolver provides a convenient way to verify that your DID is publicly accessible and correctly formatted.

## Lab 3: Creating Schemas and Credential Definitions with WebVH

<a id="lab-3-creating-schemas-and-credential-definitions-with-webvh"></a>

In this lab we will use our Traction Tenant agent to create and publish an
AnonCreds Schema object, and then use that Schema to create and publish
a Credential Definition. All of the AnonCreds objects will be published as
Attested Resources on the WebVH server. For those new to AnonCreds:

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

With WebVH, schemas and credential definitions are published as **Attested Resources**,
which are cryptographically signed and linked to your WebVH DID. These resources
can be resolved via HTTP using your DID.

### Lab 3: Steps to Follow

1. If necessary, log into your [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) with your Wallet ID and Key.
2. Create a Schema:
    1. Click the menu item "Configuration" and then "Schema Storage".
    2. Click "Create Schema" button.
    3. Fill in the schema details:
        - **Schema Name**: Enter a name for your schema (e.g., `Student ID` or `Workshop Credential`)
        - **Schema Version**: Enter a version (e.g., `1.0.0`)
        - **Attributes**: Add the attributes you want in your credential. For example:
            - `student_id` (text)
            - `name` (text)
            - `date_of_birth` (text, format: YYYYMMDD for predicate support)
            - `expiry_date` (text, format: YYYYMMDD)
        - **Issuer DID**: Select your WebVH DID from the dropdown (it should show your `did:webvh:...` identifier)
    4. Click "Submit" to create and publish the schema.
    5. Wait for the schema to be published. The schema will be:
        - Created as an AnonCreds Schema object
        - Signed with a Data Integrity Proof
        - Published as an Attested Resource on the WebVH server
        - Linked to your WebVH DID
    6. Once published, you'll see your schema in the Schema Storage table with a schema ID that includes your WebVH DID (e.g., `did:webvh:{SCID}:.../resources/{digest}`).
    7. Click the Expand (`>`) link to view schema details, and then click `>` again to "View Raw Content" to see the full schema object.
3. Create a Credential Definition:
    1. With your schema created, it's time to become an issuer. To do that, you have
       to create a Credential Definition. Click on the "+" icon in the
       "Credential Definition" column of your schema to create the Credential
       Definition (CredDef) for the Schema.
    2. In the dialog that appears:
        - **Tag**: Enter any value you want (e.g., `default` or `workshop`) — it
          is an issuer-defined part of the identifier for the Credential Definition.
        - **Support Revocation**: Enable revocation support by checking this option. This will create a revocation registry that allows you to revoke credentials if needed.
        - **Revocation Registry Size**: Set this to `4`. This determines the maximum number of credentials that can be revoked in this registry. For this workshop, a small registry size is sufficient.
    3. Click "Submit" and wait for the operation to complete.
    4. The Credential Definition will be:
        - Created with your WebVH DID as the issuer
        - Linked to your schema
        - Created with a revocation registry (size 4) for revocable credentials
        - Signed and published as an Attested Resource on the WebVH server
    5. Click the "Refresh" button if needed to see the Create icon has been replaced with the identifier for your CredDef.
4. Review your AnonCreds objects:
    1. Move to the menu item "Configuration → Credential Definition Storage" to see
       the CredDef you created. If you want, expand it to view the raw data.
    2. Both your Schema and Credential Definition are now published on the WebVH server
       and can be resolved using your WebVH DID. Unlike blockchain-based registries,
       these objects are accessible via HTTP resolution of your DID.
5. Browse your resources in the WebVH Explorer:
    1. The WebVH server provides a web-based explorer interface that allows you to
       browse and view all DIDs, resources, and credentials published on the server.
    2. Open your web browser and navigate to the WebVH Explorer. For the sandbox server,
       the URL is: `https://sandbox.bcvh.vonx.io/explorer`.
    3. In the explorer interface, you can:
        - **View DIDs**: Click on "DIDs" or navigate to the DIDs section to see all published DIDs.
          You can filter by namespace (e.g., `default`) or by the SCID value to find your DID.
        - **View Resources**: Click on "Resources" to see all published AnonCreds resources
          (schemas, credential definitions, revocation registries). Your schema and credential
          definition should appear in this list.
        - **Search**: Use the search/filter functionality to find your specific resources by:
          - Your DID identifier
          - Resource type (e.g., "anonCredsSchema" or "anonCredsCredDef")
          - Namespace
    4. Click on your schema or credential definition in the explorer to view its details:
        - The full resource content
        - The resource metadata
        - The cryptographic proof (Data Integrity Proof)
        - The resource ID (which matches the schema ID or credential definition ID you saw in Traction)
    5. This demonstrates that your AnonCreds objects are publicly accessible and can be
       discovered and resolved by anyone who knows your DID or the resource ID.

Completed all the steps? Great! Feel free to create a second Schema and Cred
Def, ideally one related to your first. That way you can try out a presentation
request that pulls data from both credentials! When you create the second
schema, use the "Create Schema" button, and add the claims you want to have in
your new type of credential.

## Lab 4: Issuing Credentials to a Mobile Wallet

<a id="lab-4-issuing-credentials-to-a-mobile-wallet"></a>

In this lab we will use our Traction Tenant agent to issue instances of the
credentials we created in [Lab 3](#lab-3-creating-schemas-and-credential-definitions-with-webvh) to our
Mobile Wallet we downloaded in [Lab
1](#lab-1-getting-a-traction-tenant-agent-and-mobile-wallet).

### Lab 4: Steps to Follow

1. If necessary, log into your [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) with your Wallet ID and Key.
2. Issue a Credential:
    1. Click the menu item "Issuance" and then "Offer a Credential".
    2. Select the Credential Definition of the credential you want to issue (the one you created in Lab 3).
    3. Select the Contact Name to whom you are issuing the credential—the alias of the connection you made to your mobile Wallet.
    4. Click the "Enter Credential Value" to popup a data entry form for the attributes to populate.
        1. When you enter the date values that you want to use in predicates
           (e.g., "Older than 19"), put the date into the following format:
           **`YYYYMMDD`**, e.g., **`20231001`**. You cannot use a string date
           format, such as "YYYY-MM-DD" if you want to use the attribute for
           predicate checking -- the value must be an integer.
        2. We suggest you use realistic dates for Date of Birth (DOB) (e.g., 20-ish
           years in the past) and expiry (e.g., 3 years in the future) to make
           using them in predicates easier.
    5. Click "Save" when you are finished entering the attributes and review the
       information you have entered.
    6. When you are ready, click "Send Offer" to initiate the issuance of the
       credential.
3. Receive the Credential:
    1. Open up your mobile Wallet and look for a notification about the credential offer. Where that appears may vary based on the Wallet you are using.
    2. Review the offer and then click the "Accept" button.
    3. Your new credential should be saved to your wallet. The credential is an AnonCreds credential that references your WebVH-published schema and credential definition.
4. Review the Issuance Data:
    1. Back in your Traction Tenant, refresh the list to see the updated status of the issuance you just completed (should be "credential_issued" or "done", depending on the Wallet you are using).
    2. Expand the issuance and again to "View Raw Content." to see the data that was exchanged between the Traction Issuer and the Wallet.
5. If you want, repeat the process for other credentials types your Traction Tenant is capable of issuing.

That's it! Pretty easy, eh? Of course, in a real issuer, the data would (very,
very) likely not be hand-entered, but instead come from a backend system.
Traction has an HTTP API (protected by the same Wallet ID and Key) that can be
used from an application, to do things like this automatically. The Traction API
embeds the ACA-Py API, so everything you can do in "plain ACA-Py" can also be
done in Traction.

## Lab 5: Requesting and Verifying Presentations

<a id="lab-5-requesting-and-verifying-presentations"></a>

In this lab we will use our Traction Tenant agent as a verifier, requesting
presentations, and your mobile Wallet as the holder responding with
presentations that satisfy the requests. The user interface is a little rougher
for this lab (you'll be dealing with JSON), but it should still be easy enough
to do.

### Lab 5: Steps to Follow

1. If necessary, log into your [Traction Sandbox](https://traction-sandbox-tenant-ui.apps.silver.devops.gov.bc.ca/) with your Wallet ID and Key.
2. Create and send a presentation request:
    1. Click the menu item "Verification" and then the button "Create Presentation Request".
    2. Select the Connection to whom you are sending the request—the alias of the connection you made to your mobile Wallet.
    3. Update the example Presentation Request to match the credential that you want to request. Keep it simple for your first request—it's easy to iterate in Traction to make your request more complicated. If you used the schema we suggested in Lab 3, update the presentation request:
         1. Update the value of "schema_name" to the name of the schema for the credential you issued.
         2. Update the group name(s) to something that makes sense for your credential(s) and make sure the attributes listed match your credential(s).
         3. Update (or perhaps remove) the "request_predicates" JSON item, if it is not applicable to your credential.
    4. **Sample Presentation Request JSON** (for reference):
       ```json
       {
         "name": "Student ID Verification",
         "version": "1.0",
         "requested_attributes": {
           "student_id_group": {
             "name": "student_id",
             "names": ["student_id", "name"],
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "requested_predicates": {}
       }
       ```
       Or with predicates:
       ```json
       {
         "name": "Student ID Verification with Age Check",
         "version": "1.0",
         "requested_attributes": {
           "student_id_group": {
             "name": "student_id",
             "names": ["student_id", "name"],
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "requested_predicates": {
           "age_check": {
             "name": "date_of_birth",
             "p_type": ">=",
             "p_value": 20030527,
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         }
       }
       ```
       Replace `YOUR_CRED_DEF_ID` with your actual credential definition ID. The `names` array lists all attributes that will be revealed from the same credential. Predicates allow you to prove relationships (like age >= 19) without revealing the exact value.
    5. Update the optional fields ("Auto Verify" and "Optional Comment") as you see fit. The "Optional Comment" goes into the list of Verifications so you can keep track of the different presentation requests you create.
    6. Click "Submit" when your presentation request is ready.
3. Respond to the Presentation Request:
    1. Open up your mobile Wallet and look for a notification about receiving a presentation request. Where that appears may vary based on the Wallet you are using.
    2. Review the information you are being asked to share, and then click the "Share" button to send the presentation.
    3. The wallet will resolve your WebVH DID to find the schema and credential definition, create an AnonCreds presentation, and send it back to your Traction Tenant.
4. Review the Presentation Request Result:
    1. Back in your Traction Tenant, refresh the Verifications list to see the updated status of the presentation request you just completed. It should be something positive, like "presentation_received" or "done" if all went well. It may be different depending on the Wallet you are using.
    2. If you want, expand the presentation request and "View Raw Content." to see the presentation request, and presentation data exchanged between the Traction Verifier and the Wallet.
    3. The verification process will resolve your WebVH DID to retrieve the schema and credential definition, then verify the AnonCreds presentation against those objects.
5. Repeat the process, making the presentation request more complicated:
    1. From the list of presentations, use the arrow icon action to copy an existing presentation request and just re-run it, or evolve it.
    2. Ideas:
       1. Add predicates using date of birth ("older than") and expiry ("not expired today").
           1. The **`p_value`** should be a relevant date — e.g., 19 (or whatever) years ago today for "older than", and today for "not expired", both in the **`YYYYMMDD`** format (the integer form of the date).
           2. The **`p_type`** should be **`>=`** for the "older than", and **`=<`** for "not expired".  See the table below for the form of the expression form.
    3. Add a second credential group with a restriction for a different credential to the request, so the presentation is derived from two source credentials.

| p_value  | p_type | credential_data |
| -------- | ------ | --------------- |
| 20230527 | <=     | expiry_dateint  |
| 20030527 | >=     | dob_dateint     |

That completes this lab — although feel free to continue to play with all of the steps (setup, issuing and presenting). You should have a pretty solid handle on exactly what you can and can't do with AnonCreds using WebVH!

### Lab 5A: Revoking Credentials and Exploring Revocation Entries (Bonus Lab)

<a id="lab-5a-revoking-credentials-and-exploring-revocation-entries"></a>

In this bonus lab, we'll explore credential revocation—an important feature that allows issuers to revoke credentials when necessary (e.g., if a credential is lost, compromised, or no longer valid). With WebVH, revocation registry entries are published as Attested Resources, making them publicly verifiable.

#### Lab 5A: Steps to Follow

1. **Navigate to Issued Credentials**:
   - In your Traction Tenant UI, navigate to "Profile" → "Issuance" → "Credentials"
   - You should see a table listing all credentials you've issued (from Lab 4)
   - Find a credential that was successfully issued (Status should be "Done")
   - Note: The credential must have been issued with revocation support (which we enabled in Lab 3)
   - Expand the row by clicking the expander arrow to see detailed information
   - Note the `rev_reg_id` (Revocation Registry ID) and `cred_rev_id` (Credential Revocation ID) from the expanded details - you'll need these later

2. **Revoke a Credential Using the Traction UI**:
   - In the "Actions" column for your selected credential, click the revoke button (circle with an X icon)
   - A modal dialog will open showing:
     - Connection information
     - Revocation ID (`cred_rev_id`)
     - Revocation Registry ID (`rev_reg_id`)
   - Enter a comment explaining why you're revoking (e.g., "Credential revoked for testing purposes")
   - Click the "Revoke" button
   - The revocation will be:
     - Published to the WebVH registry automatically (`publish: true`)
     - A notification will be sent to the holder (`notify: true`)
   - You should see a success message confirming the credential has been revoked
   - The credential status may update to reflect the revocation

3. **Verify Revocation Status**:
   - Refresh the credentials table to see updated information
   - Expand the revoked credential row again to see the updated details
   - The credential should now show revocation information
   - You can also check the WebVH Explorer (step 5) to see the published revocation entry

4. **Request a Presentation to Verify Revocation Check**:
   - Navigate to "Profile" → "Verification" → "Presentations"
   - Create a new presentation request (as in Lab 5) that includes revocation checking
   - When creating the presentation request:
     - Select the connection with your mobile wallet
     - Select the credential definition for the credential you just revoked
     - In the presentation request options, ensure revocation checking is enabled
     - The presentation request should include a `non_revoked` time range check
   - Send this request to your wallet
   - The wallet should check revocation status and either:
     - Reject the presentation if the credential is revoked (which it should be)
     - Accept it if the credential is still valid (which shouldn't happen in this case)
   - Try creating another presentation request for a credential that hasn't been revoked - it should be accepted

5. **Explore Revocation Entries on WebVH Server**:
   - Navigate to the WebVH Explorer: `https://sandbox.bcvh.vonx.io/explorer`
   - Click on "Resources" to see all published resources
   - Filter by resource type to find revocation-related resources:
     - Look for resources with type `anonCredsRevRegDef` (Revocation Registry Definition)
     - Look for resources with type `anonCredsRevList` (Revocation List/State)
   - You can also filter by your WebVH DID to see resources associated with your issuer
   - Click on a revocation registry definition to see:
     - The registry ID (should match the `rev_reg_id` from your credential)
     - Maximum number of credentials (should be 4, as we set in Lab 3)
     - Public keys for revocation
   - Click on a revocation list/state to see:
     - The current revocation accumulator
     - Timestamp of the last update
     - Links to previous revocation states (showing the history)
   - Notice how revocation entries are linked together, creating a verifiable history
   - If you've revoked a credential, you should see an updated revocation state entry

6. **Understand Revocation Registry Structure**:
   - Each revocation registry has a definition (published when the credential definition was created in Lab 3)
   - Revocation states are published as separate resources, linked together
   - Each revocation state update includes:
     - The current accumulator (cryptographic structure)
     - Timestamp of the update
     - Links to previous states
   - This allows verifiers to check revocation status without revealing which specific credential they're checking
   - The revocation registry can hold up to 4 credentials (as we configured), and you can see how many have been issued and revoked

7. **Try Revoking Another Credential**:
   - Issue a new credential (using Lab 4 steps) if you haven't already
   - Navigate back to "Profile" → "Issuance" → "Credentials"
   - Find the newly issued credential
   - Revoke it using the revoke button in the Actions column
   - Add a comment and confirm the revocation
   - Check the WebVH Explorer again - you should see the revocation count increase
   - Explore the new revocation state entry in the WebVH Explorer to see the updated accumulator

### What You've Learned in Lab 5A

In this bonus lab, you've learned:

1. **Revoke Credentials**: How to revoke credentials using the Traction UI
2. **Check Revocation Status**: How to verify if a credential has been revoked
3. **Revocation Registry Structure**: Understanding how revocation registries work
4. **WebVH Revocation Resources**: How revocation entries are published as Attested Resources on WebVH
5. **Revocation History**: How revocation states are linked together, creating a verifiable history
6. **Privacy-Preserving Revocation**: How revocation checks can be done without revealing which credential is being checked
7. **Presentation with Revocation Checks**: How to verify that revoked credentials are properly rejected in presentation requests

## Part 2: OpenAPI (Swagger) Demo - Programmatic WebVH Operations

In this second part of the workshop, we'll explore how to use the OpenAPI (Swagger) interface to programmatically interact with your Traction tenant and WebVH resources. This demonstrates how to automate credential issuance, verification, and WebVH operations using REST APIs.

### Prerequisites for Part 2

Before starting this demo, you'll need:

1. Completed Part 1 (Labs 1-5) - You should have:
   - A Traction tenant with WebVH configured
   - A WebVH DID created
   - At least one schema and credential definition published
   - A connection to your mobile wallet
2. Basic familiarity with web browsers and JSON
3. Your Traction tenant API credentials (JWT token from Developer menu)

### Lab 6: Accessing the OpenAPI Interface

<a id="lab-6-accessing-the-openapi-interface"></a>

In this lab, we'll learn how to access and use the OpenAPI (Swagger) interface for your Traction tenant to interact with WebVH resources programmatically.

#### Lab 6: Steps to Follow

1. **Get Your API Credentials**:
   - In your Traction Tenant, click the User icon (top right) and choose "Developer"
   - Scroll to the bottom and expand the "Encoded JWT", and click the "Copy" icon to the right to get the JWT into your clipboard.
   - **Important**: By using the "copy" icon, the JWT is prefixed with "Bearer ", which is needed in the OpenAPI authorization. If you just highlight and copy the JWT, you don't get the prefix.
   - Save this JWT token - you'll need it for API calls.

2. **Access the Swagger UI**:
   - Click on "About" from the left menu and then click "Traction."
   - Click on the link with the "Swagger URL" label to open up the OpenAPI (Swagger) API.
   - The URL is: `https://traction-sandbox-tenant-proxy.apps.silver.devops.gov.bc.ca/api/doc`
   - Bookmark this page for easy access.

3. **Authorize in Swagger**:
   - Click "Authorize" in the top right of the Swagger UI
   - Click in the second box "AuthorizationHeader (apiKey)" 
   - Paste your previously copied encoded JWT (with "Bearer " prefix)
   - Click "Authorize" and then "Close"

4. **Explore WebVH Endpoints**:
   - Search for "webvh" in the Swagger search box
   - Try these endpoints:
     - `GET /did/webvh/configuration` - Get your WebVH configuration
     - `GET /did/webvh/identifiers` - List your WebVH DIDs
     - `POST /did/webvh/create` - Create a new WebVH DID
     - `GET /anoncreds/registries` - List available AnonCreds registries (should include WebVH)

5. **Test an Endpoint**:
   - Click on `GET /did/webvh/identifiers` to expand it
   - Click "Try it out"
   - Click "Execute"
   - You should see a list of your WebVH DIDs in the response

6. **Explore AnonCreds Endpoints**:
   - Search for "anoncreds" or "schema" in Swagger
   - Try `GET /anoncreds/registry/{registry_id}/schemas` to see your published schemas
   - Try `GET /anoncreds/registry/{registry_id}/credential-definitions` to see your credential definitions
   - Note: The `registry_id` for WebVH will be your WebVH DID

### Lab 7: Using the API to Issue Credentials Programmatically

<a id="lab-7-using-the-api-to-issue-credentials-programmatically"></a>

In this lab, we'll use the Swagger UI to issue credentials directly through the API interface.

#### Lab 7: Steps to Follow

1. **Get Your Connection ID**:
   - In Swagger UI, find and expand `GET /connections`
   - Click "Try it out"
   - Click "Execute"
   - Find your mobile wallet connection in the response
   - Copy the `connection_id` value - you'll need this to issue credentials
   - Note: The connection should have `state: "active"` for issuance to work

2. **Get Your Credential Definition ID**:
   - First, get your WebVH registry ID (your WebVH DID):
     - Expand `GET /did/webvh/identifiers`
     - Click "Try it out" → "Execute"
     - Copy one of the `did` values from the results
   - Now get your credential definitions:
     - Expand `GET /anoncreds/registry/{registry_id}/credential-definitions`
     - Click "Try it out"
     - Paste your WebVH DID into the `registry_id` parameter
     - Click "Execute"
     - Copy one of the `credential_definition_ids` from the response

3. **Issue a Credential Using Swagger**:
   - Find and expand `POST /issue-credential-2.0/send-offer`
   - Click "Try it out"
   - In the request body, replace the example JSON with (replace the placeholder values):
   ```json
   {
     "connection_id": "YOUR_CONNECTION_ID",
     "credential_preview": {
       "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
       "attributes": [
         {"name": "student_id", "value": "ST-2024-001"},
         {"name": "name", "value": "Alice Smith"},
         {"name": "date_of_birth", "value": "20030527"},
         {"name": "expiry_date", "value": "20271231"}
       ]
     },
     "filter": {
       "anoncreds": {
         "cred_def_id": "YOUR_CRED_DEF_ID"
       }
     }
   }
   ```
   - Replace `YOUR_CONNECTION_ID` with the connection ID you copied in step 1
   - Replace `YOUR_CRED_DEF_ID` with the credential definition ID you copied in step 2
   - Update the attribute values to match your schema
   - Click "Execute"
   - You should see a successful response with a credential exchange record
   - Check your mobile wallet - you should receive a credential offer notification

4. **Check the Credential Exchange Status**:
   - Find and expand `GET /issue-credential-2.0/records`
   - Click "Try it out" → "Execute"
   - Find your credential exchange in the list
   - The `state` field shows the current status (e.g., "offer_sent", "credential_issued")
   - Expand the record to see all the details
   - Wait for the wallet to accept the credential - the state should change to "credential_issued" or "done"

5. **Verify Credential Issuance**:
   - Once the credential is issued, check your mobile wallet to confirm it was received
   - You can also check the credential exchange record again to see the updated state
   - The response will include details about the issued credential

### Lab 8: Using the API to Request Presentations Programmatically

<a id="lab-8-using-the-api-to-request-presentations-programmatically"></a>

In this lab, we'll use the Swagger UI to create and send presentation requests directly through the API interface.

#### Lab 8: Steps to Follow

1. **Get Your Connection ID** (if you don't have it from Lab 7):
   - In Swagger UI, find and expand `GET /connections`
   - Click "Try it out" → "Execute"
   - Find your mobile wallet connection in the response
   - Copy the `connection_id` value

2. **Get Your Credential Definition ID** (if you don't have it from Lab 7):
   - Expand `GET /did/webvh/identifiers` → "Try it out" → "Execute"
   - Copy your WebVH DID
   - Expand `GET /anoncreds/registry/{registry_id}/credential-definitions`
   - Paste your WebVH DID into `registry_id` → "Execute"
   - Copy one of the `credential_definition_ids`

3. **Create a Presentation Request Using Swagger**:
   - Find and expand `POST /present-proof-2.0/send-request`
   - Click "Try it out"
   - In the request body, use this JSON (replace placeholder values):
   
   **Basic Presentation Request Example:**
   ```json
   {
     "connection_id": "YOUR_CONNECTION_ID",
     "comment": "Please share your student ID credential",
     "presentation_request": {
       "anoncreds": {
         "name": "Proof Request",
         "version": "1.0",
         "requested_attributes": {
           "student_id": {
             "name": "student_id",
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "requested_predicates": {}
       }
     },
     "auto_verify": true
   }
   ```
   
   **Complete Presentation Request Example (with multiple attributes and predicates):**
   ```json
   {
     "connection_id": "YOUR_CONNECTION_ID",
     "comment": "Please share your student credential",
     "presentation_request": {
       "anoncreds": {
         "name": "Student ID Verification",
         "version": "1.0",
         "requested_attributes": {
           "student_info": {
             "names": ["student_id", "name"],
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "requested_predicates": {
           "age_check": {
             "name": "date_of_birth",
             "p_type": ">=",
             "p_value": 20030527,
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           },
           "expiry_check": {
             "name": "expiry_date",
             "p_type": ">=",
             "p_value": 20240101,
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "non_revoked": {
           "from": 1735689600,
           "to": 1735689600
         }
       }
     },
     "auto_verify": true
   }
   ```
   
   **Field Explanations:**
   - `connection_id`: The connection ID of the wallet you're requesting from
   - `comment`: Optional human-readable message for the wallet holder
   - `presentation_request.anoncreds.name`: Name of the proof request
   - `presentation_request.anoncreds.version`: Version of the proof request format
   - `presentation_request.anoncreds.requested_attributes`: Attributes to be revealed (each needs a unique key)
     - `name`: The attribute name from your schema
     - `names`: Array of attribute names from your schema (for revealing multiple attributes from the same credential)
     - `restrictions`: Array of restrictions (credential definition IDs that can satisfy this)
   - `presentation_request.anoncreds.requested_predicates`: Predicate proofs for privacy-preserving checks
     - `name`: The attribute name to check
     - `p_type`: Predicate type (`>=`, `>`, `<=`, `<`)
     - `p_value`: The value to compare against (must be an integer, use YYYYMMDD format for dates)
     - `restrictions`: Array of restrictions (credential definition IDs that can satisfy this)
   - `presentation_request.anoncreds.non_revoked`: Optional time range to check revocation status
     - `from`: Start timestamp (Unix epoch time)
     - `to`: End timestamp (Unix epoch time)
   - `auto_verify`: Automatically verify the presentation when received
   
   - Replace `YOUR_CONNECTION_ID` with your connection ID
   - Replace `YOUR_CRED_DEF_ID` with your credential definition ID
   - Adjust attribute names to match your schema
   - Update predicate values (dates should be in YYYYMMDD integer format)
   - Click "Execute"
   - You should see a successful response with a presentation exchange record
   - Check your mobile wallet - you should receive a presentation request notification

4. **Check the Presentation Exchange Status**:
   - Find and expand `GET /present-proof-2.0/records`
   - Click "Try it out" → "Execute"
   - Find your presentation exchange in the list
   - The `state` field shows the current status (e.g., "request_sent", "presentation_received")
   - Wait for the wallet to share the presentation - the state should change to "presentation_received" or "done"

5. **Verify Presentation**:
   - Once the presentation is received, expand the exchange record to see the details
   - The response will include the revealed attributes from the credential
   - If you set `auto_verify` to true (or verify manually), you'll see verification results

6. **Try a More Complex Presentation Request**:
   - Create another presentation request with predicates:
   ```json
   {
     "connection_id": "YOUR_CONNECTION_ID",
     "comment": "Please prove your age",
     "presentation_request": {
       "anoncreds": {
         "name": "Proof Request with Predicates",
         "version": "1.0",
         "requested_attributes": {
           "student_id": {
             "name": "student_id",
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         },
         "requested_predicates": {
           "age_check": {
             "name": "date_of_birth",
             "p_type": ">=",
             "p_value": 20030527,
             "restrictions": [{
               "cred_def_id": "YOUR_CRED_DEF_ID"
             }]
           }
         }
       }
     },
     "auto_verify": true
   }
   ```
   - This requests the student_id attribute and proves the date_of_birth is >= 20030527 (without revealing the exact date)
   - Replace `YOUR_CONNECTION_ID` and `YOUR_CRED_DEF_ID` with your actual values
   - Click "Execute" to send the request

7. **Explore More Endpoints**:
   - Try `GET /anoncreds/registry/{registry_id}/schemas` to see your published schemas
   - Try `GET /did/webvh/configuration` to see your WebVH configuration
   - Browse other endpoints to understand the full API capabilities

### Lab 9: Revoking Credentials and Exploring Revocation Entries (Bonus Lab)

<a id="lab-9-revoking-credentials-and-exploring-revocation-entries"></a>

In this bonus lab, we'll explore credential revocation—an important feature that allows issuers to revoke credentials when necessary (e.g., if a credential is lost, compromised, or no longer valid). With WebVH, revocation registry entries are published as Attested Resources, making them publicly verifiable.

#### Lab 9: Steps to Follow

1. **Get Credential Exchange Information**:
   - In Swagger UI, find and expand `GET /issue-credential-2.0/records`
   - Click "Try it out" → "Execute"
   - Find a credential that was issued (from Lab 7) and copy its `cred_ex_id`
   - Note: The credential must have been issued with revocation support (which we enabled in Lab 3)
   - Also note the `rev_reg_id` and `cred_rev_id` from the credential exchange record - you'll need these

2. **Revoke a Credential Using Swagger**:

   There are two ways to revoke a credential, depending on whether the credential exchange record still exists:

   **Option A: Revoke Using Credential Exchange ID** (when the exchange record exists):
   
   - Find and expand `POST /anoncreds/revocation/revoke`
   - Click "Try it out"
   - In the request body, use this JSON:
   ```json
   {
     "cred_ex_id": "YOUR_CRED_EX_ID",
     "publish": true,
     "notify": true,
     "comment": "Credential revoked for testing purposes"
   }
   ```
   - Replace `YOUR_CRED_EX_ID` with the credential exchange ID you copied in step 1
   - The `publish: true` flag ensures the revocation is published to the WebVH registry
   - The `notify: true` flag sends a revocation notification to the holder
   - Click "Execute"
   - You should see a successful response indicating the credential has been revoked

   **Option B: Revoke Using Connection ID and Credential Definition ID** (when the exchange record has been deleted):
   
   If the credential exchange record has been deleted, you'll need to look up the revocation information first:
   
   a. **Find the Revocation Registry ID and Credential Revocation ID**:
      - Find and expand `GET /issue-credential-2.0/records`
      - Click "Try it out" → "Execute"
      - In the response, find a credential that matches:
        - `connection_id`: The connection ID of the holder
        - `credential_definition_id`: The credential definition ID (check the `anoncreds.cred_def_id` field)
      - From that credential record, copy:
        - `rev_reg_id` (from `anoncreds.rev_reg_id`)
        - `cred_rev_id` (from `anoncreds.cred_rev_id`)
        - `connection_id` (from `cred_ex_record.connection_id`)
   
   b. **Revoke Using the Revocation Information**:
      - Find and expand `POST /anoncreds/revocation/revoke`
      - Click "Try it out"
      - In the request body, use this JSON:
      ```json
      {
        "rev_reg_id": "YOUR_REV_REG_ID",
        "cred_rev_id": "YOUR_CRED_REV_ID",
        "connection_id": "YOUR_CONNECTION_ID",
        "publish": true,
        "notify": true,
        "comment": "Credential revoked for testing purposes"
      }
      ```
      - Replace `YOUR_REV_REG_ID` with the revocation registry ID you found
      - Replace `YOUR_CRED_REV_ID` with the credential revocation ID you found
      - Replace `YOUR_CONNECTION_ID` with the connection ID (required when `notify: true`)
      - The `publish: true` flag ensures the revocation is published to the WebVH registry
      - The `notify: true` flag sends a revocation notification to the holder (requires `connection_id`)
      - Click "Execute"
      - You should see a successful response indicating the credential has been revoked
   
   **Note:** If you don't have the credential exchange record and can't find it in the issued credentials list, you can also query the revocation registry directly:
   - Use `GET /anoncreds/revocation/registry/{rev_reg_id}/issued/details` to see all credentials issued against a revocation registry
   - Find the credential you want to revoke by matching the connection or other identifying information
   - Extract the `cred_rev_id` from the results

3. **Verify Revocation Status**:
   - Find and expand `GET /anoncreds/revocation/registry/{rev_reg_id}`
   - Click "Try it out"
   - Paste your `rev_reg_id` into the parameter
   - Click "Execute"
   - Review the revocation registry details, including:
     - Total credentials issued
     - Total credentials revoked
     - Current state of the revocation registry

4. **Check Revoked Credentials**:
   - Find and expand `GET /anoncreds/revocation/registry/{rev_reg_id}/issued/details`
   - Click "Try it out"
   - Paste your `rev_reg_id` into the parameter
   - Click "Execute"
   - You should see a list of all credentials issued against this registry
   - Find your revoked credential in the list - it should show as revoked

5. **Request a Presentation to Verify Revocation Check**:
   - Create a new presentation request (as in Lab 8) that includes revocation checking
   - Find and expand `POST /present-proof-2.0/send-request`
   - Click "Try it out"
   - The presentation request should include `non_revoked` in the request:
   ```json
   {
     "name": "Proof Request with Revocation Check",
     "version": "1.0",
     "requested_attributes": {
       "student_id": {
         "name": "student_id",
         "restrictions": [{
           "cred_def_id": "YOUR_CRED_DEF_ID"
         }]
       }
     },
     "requested_predicates": {},
     "non_revoked": {
       "from": 0,
       "to": 1735689600
     }
   }
   ```
   **Note:** When using this in the Swagger UI, wrap this JSON in a `presentation_request` object with an `anoncreds` key, and include `connection_id` and `auto_verify`:
   ```json
   {
     "connection_id": "YOUR_CONNECTION_ID",
     "presentation_request": {
       "anoncreds": { ...the JSON above... }
     },
     "auto_verify": true
   }
   ```
   - Replace `YOUR_CONNECTION_ID` with your connection ID
   - Replace `YOUR_CRED_DEF_ID` with your credential definition ID
   - Click "Execute"
   - Send this request to your wallet
   - The wallet should check revocation status and either:
     - Reject the presentation if the credential is revoked
     - Accept it if the credential is still valid

6. **Explore Revocation Entries on WebVH Server**:
   - Navigate to the WebVH Explorer: `https://sandbox.bcvh.vonx.io/explorer`
   - Click on "Resources" to see all published resources
   - Filter by resource type to find revocation-related resources:
     - Look for resources with type `anonCredsRevRegDef` (Revocation Registry Definition)
     - Look for resources with type `anonCredsRevList` (Revocation List/State)
   - Click on a revocation registry definition to see:
     - The registry ID
     - Maximum number of credentials
     - Public keys for revocation
   - Click on a revocation list to see:
     - The current revocation accumulator
     - Timestamp of the last update
     - Links to previous revocation states (showing the history)
   - Notice how revocation entries are linked together, creating a verifiable history

7. **Understand Revocation Registry Structure**:
   - Each revocation registry has a definition (published when the credential definition was created)
   - Revocation states are published as separate resources, linked together
   - Each revocation state update includes:
     - The current accumulator (cryptographic structure)
     - Timestamp of the update
     - Links to previous states
   - This allows verifiers to check revocation status without revealing which specific credential they're checking

8. **Try Revoking Another Credential**:
   - Issue a new credential (using Lab 7 steps)
   - Revoke it using the Swagger UI
   - Check the revocation registry again - you should see the revoked count increase
   - Explore the new revocation state entry in the WebVH Explorer

### What You've Learned in Lab 9

In this bonus lab, you've learned:

1. **Revoke Credentials**: How to revoke credentials programmatically using the API
2. **Check Revocation Status**: How to verify if a credential has been revoked
3. **Revocation Registry Structure**: Understanding how revocation registries work
4. **WebVH Revocation Resources**: How revocation entries are published as Attested Resources on WebVH
5. **Revocation History**: How revocation states are linked together, creating a verifiable history
6. **Privacy-Preserving Revocation**: How revocation checks can be done without revealing which credential is being checked

### What You've Learned

In Part 2, you've learned how to:

1. **Access the OpenAPI Interface**: Use the Swagger UI to explore and test API endpoints
2. **Authenticate API Calls**: Use JWT tokens to authenticate with the Traction API
3. **Query WebVH Resources**: Retrieve DIDs, schemas, and credential definitions through the API
4. **Issue Credentials Programmatically**: Issue credentials directly through the Swagger UI using the API
5. **Request Presentations Programmatically**: Create and send presentation requests using the API interface
6. **Monitor Exchanges**: Check the status of credential and presentation exchanges through the API
7. **Use Predicates**: Create presentation requests with predicate proofs for privacy-preserving verification

### Next Steps

- Explore more endpoints in the Swagger UI (connections, messages, wallet operations)
- Try issuing credentials with different attribute values
- Experiment with presentation requests that include predicates
- Use the API to automate your credential issuance workflow
- Integrate these API calls into your own applications using the same endpoints

## What's Next

<a id="whats-next"></a>

The following are a couple of things that you might want to do next--if you are
a developer. Unlike the labs you have just completed, these "next steps" are
geared towards developers, providing details about building the use of
verifiable credentials (issuing, verifying) into your own application.

Want to use [Traction](https://digital.gov.bc.ca/digital-trust/technical-resources/traction/) in your own environment? Feel free! It's open source, and
comes with Helm Charts for easy deployment in container-orchestrated
environments. Contributions back to the project are always welcome!

### What's Next: The ACA-Py OpenAPI

Are you going to build an app that uses Traction or an instance of [ACA-Py](https://aca-py.org/)? If so, your next step is to try out the ACA-Py OpenAPI (aka Swagger)—by hand at first, and then from your application. This is a VERY high level overview, assuming a developer is following this, and knows a bunch about verifiable credential protocols, using HTTP APIs, and using OpenAPI interfaces.

To access and use your Tenant's OpenAPI (aka Swagger) interface:

* In your Traction Tenant, click the User icon (top right) and choose "Developer"
* Scroll to the bottom and expand the "Encoded JWT", and click the "Copy" icon to the right to get the JWT into your clipboard.
  * By using the "copy" icon, the JWT is prefixed with "Bearer ", which is needed in the OpenAPI authorization. If you just highlight and copy the JWT, you don't get the prefix.
* Click on "About" from the left menu and then click "Traction."
* Click on the link with the "Swagger URL" label to open up the OpenAPI (Swagger) API.
  * The URL is just the normal [Traction Tenant API with `"api/doc"](https://traction-sandbox-tenant-proxy.apps.silver.devops.gov.bc.ca/api/doc) added to it.
* Click Authorize in the top right, click in the second box "AuthorizationHeader (apiKey)" and paste in your previously copied encoded JWT.
* Close the authorization window and try out an Endpoint. For example, scroll down to the "GET /connections" endpoint, "Try It Out" and "Execute".  You should get back a list of the connections you have established in your Tenant.

The ACA-Py/Traction API is pretty large, but it is reasonably well organized, and you should recognize from the Traction API a lot of the items. Try some of the "GET" endpoints to see if you recognize the items. You can also explore the WebVH-specific endpoints:

* `GET /did/webvh/configuration` - Get your WebVH configuration
* `POST /did/webvh/create` - Create a new WebVH DID
* `GET /anoncreds/registries` - List available AnonCreds registries (should include WebVH)

We're still working on a good demo for the OpenAPI from Traction, but [this one
from
ACA-Py](https://aca-py.org/main/demo/OpenAPIDemo/#using-the-openapiswagger-user-interface)
is a good outline of the process. It doesn't use your Traction Tenant, but you
should get the idea about the sequence of calls to make to accomplish verifiable credential
activities. For example, see if you can carry out the steps to do the [Lab
4](#lab-4-issuing-and-verifying-credentials) with your mobile agent by
invoking the right sequence of OpenAPI calls.

### What's Next: Understanding WebVH Resolution

One of the key differences between WebVH and blockchain-based registries is how
objects are resolved. With WebVH:

1. **DID Resolution**: Your WebVH DID (e.g., `did:webvh:{SCID}:sandbox.bcvh.vonx.io:default:my-issuer`)
   is resolved via HTTP by fetching `https://{domain}/{namespace}/{identifier}/did.json`
   or `https://{domain}/{namespace}/{identifier}/did.jsonl`

2. **Resource Resolution**: AnonCreds objects (schemas, credential definitions) are
   published as Attested Resources and can be resolved using the resource ID
   (e.g., `did:webvh:{SCID}:.../resources/{digest}`) by fetching from the WebVH server.

3. **Witness Attestation**: The witness service signs DID creation and updates,
   providing cryptographic attestation without requiring blockchain consensus.

You can explore WebVH resolution by:
- Viewing your DID document: `https://sandbox.bcvh.vonx.io/{namespace}/{identifier}/did.json`
- Inspecting published resources via the WebVH server API
- Understanding how wallets resolve your DID to find schemas and credential definitions

### What's Next: Experiment With an Issuer Web App

If you are challenged to use Traction or [ACA-Py](https://aca-py.org) to become an
issuer, you will likely be building API calls into your Line of Business web
application. To get an idea of what that will entail, we're delighted to direct
you to a very simple Web App that one of your predecessors on this same journey
created (and contributed!) to learn more about using the Traction OpenAPI in a
very simple Web App. Checkout this [Traction Issuance Demo] and try it out
yourself, with your Sandbox tenant. Once you review the code, you should have an
excellent idea of how you can add these same capabilities to your line of
business application.

[Traction Issuance Demo]: https://github.com/openwallet-foundation/acapy-controllers/tree/main/TractionIssuanceDemo

