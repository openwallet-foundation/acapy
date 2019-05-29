# Running the Indy CLI and Creating DIDs

- [Running the Indy CLI and Creating DIDs](#running-the-indy-cli-and-creating-dids)
  - [Starting the CLI](#starting-the-cli)
  - [Creating DID's in a Local Wallet](#creating-dids-in-a-local-wallet)
  - [Creating a DID for the Sovrin Live Network](#creating-a-did-for-the-sovrin-live-network)
    - [Creating the Seeds](#creating-the-seeds)
    - [Sharing the Seeds](#sharing-the-seeds)
    - [Generate the DID and Verkey](#generate-the-did-and-verkey)
    - [Getting the DID Published to the SLN](#getting-the-did-published-to-the-sln)
  - [Connecting to a Ledger](#connecting-to-a-ledger)
  - [Writing DID's to a Ledger](#writing-dids-to-a-ledger)
  - [Connecting to a Postgres Wallet](#connecting-to-a-postgres-wallet)
  - [Rotating a Wallet's Encryption Keys](#rotating-a-wallets-encryption-keys)
  - [Exporting and Importing a Wallet](#exporting-and-importing-a-wallet)

This document describes how to create DIDs using the Indy-CLI and how to get those DIDs loaded on other Indy Ledger - especially the Sovrin Live Network (SLN).

## Starting the CLI

You can run the CLI from any container built from von-image (which contains the Indy-CLI), as follows:

```
docker exec -it <tob-api docker image> bash
indy-cli
```

Use "help" to get more info for any command, for example:

```
help
wallet help
pool create help
```

... Etc.

## Creating DID's in a Local Wallet

You need a wallet to start creating DID's.  Create a local SQLite wallet with the following CLI commands:

```
wallet create my_wallet key
wallet open my_wallet key
```

The CLI will prompt you for the actual "key" - you can use whatever you want, but make sure you type in the same value when you create and open the wallet.  If you forget the "key", you will not be able to open the wallet!

To create a DID from a seed using the following:

```
did new seed=000000000000000000000000Trustee1
did new seed=00000000000000000000000087654321
did list
```

The first DID is the Trustee created by default in VON-Network, and is required if you want to write anything to the (VON-Network) ledger.  Make a note of the DID that is created from the "trustee" seed!

If you aren't using these DIDs for the Sovrin Live Network, you can skip the next section.

## Creating a DID for the Sovrin Live Network

To create DIDs for the Sovrin Live network, you use the same technique described above, but you need to make more random seeds, handle the seeds very carefully, and prep the DIDs and verkeys to share with Sovrin Stewards for publishing.

### Creating the Seeds

To generate random seeds, use the following commands in an interactive python session to create a seed for Registries (Onbis in Ontario) and your TheOrgBook instance:

```
>>> import os, base64
>>> base64.b64encode(os.urandom(32))
b'vR2MAsvJthgD48Kc601OS8Dnh/VrmV44C6Q986Xk/QY='
```

> **NOTE:** Make sure you know which seed is for which DID. For example, perhaps embed "TOB" and "REG" somewhere in the seeds. Note that the seeds MUST remain 32 characters long.

> Aside: Because of the state of VON_Anchor and VON-X, BC created three DIDs - including an extra one for TheOrgBook. Future instances will need only two.

### Sharing the Seeds

Once you have each seed, save them somewhere reliable (e.g. LastPass, 1Pass, etc.) and share them as little as possible.  

The seeds will have to be securely shared (e.g. in a password-protected ZIP) with whomever needs it for deployment. In the BC OpenShift world, that's just Wade. Wade will likewise securely manage the seeds.

While the seeds are important now, the DIDs will eventually have their keys rotated, these seeds will then have no value.  However, while we have tested key rotation, we have not set up a key rotation process, so key rotation will not be something done immediately.

### Generate the DID and Verkey

Once you have the seeds, use the directions above to generate the keys and get back the DIDs and associated verkeys.  Again - make sure you track which DID is for which service.

Save the DIDs and verkeys in the following format that will be sent in an email to some Sovrin Stewards:

```
send NYM dest=<DID1> role=TRUST_ANCHOR verkey=<verkey1>
send NYM dest=<DID2> role=TRUST_ANCHOR verkey=<verkey2>
```

The verkey will begin with a "~" -- be sure to include that in the text.

> Note: The DIDs and verkeys are public information and so do not need to be secured as the seed does. From the seed you can get the private key, hence why it needs to be handled carefully.

### Getting the DID Published to the SLN

When you are ready to have the DIDs published to the SLN, send an email to at least Nathan George and Phil Windley of the Sovrin Foundation (nage@sovrin.org, pjw@sovrin.org) with some context about the request and the two `send NYM...` commands above. Tney will in turn engage one or more Sovrin Trustees to process the DIDs.  "Processing" in this case means basically doing the CLI steps below to post them to the SLN Ledger. To do that, they must know a Trustee's private key - hence why only they can do the publishing. Sovrin should be able to do the publishing within about 24 hours of you sending the request - especially if they are expecting the request.

This task can be run at any time. It does not need to be synchronized with the launching.  As long as you don't lose the seeds between publishing them and launching, this can happen now.

Assuming all goes well - when the Registries and TheOrgBook production launches, those instances will find and control those DIDs, and be able to do the rest of the required ledger interactions - create schema and credential definitions.

## Connecting to a Ledger

First get a hold of the genesis file for your ledger, and save it somewhere locally (for example save it to "/tmp/genesis.json").  For example, you can download the BCovrin Dev genesis file from "http://dev.greenlight.bcovrin.vonx.io/genesis".

Then create a pool and connect to the ledger with the following CLI commands (substitute your own pool name and genesis file location):

```
pool create my_pool gen_txn_file=/tmp/genesis.json
pool connect my_pool
```

If you are connecting to an older pool you can use:

```
pool connect my_pool protocol-version=1
```

## Writing DID's to a Ledger

First you need to "did use" to enable the Trustee role:

```
did use <the trustee DID>
```

If you can't remember the Trustee DID, you can run "did list".

Then, to write a DID to the ledger:

```
ledger nym did=<something> verkey=<~something else> role=<???>
ledger nym did=<something> role=<???>
```

There are other options, check out "ledger nym help".  If you get an error message you probably "did used" the wrong DID.

## Connecting to a Postgres Wallet

To connect to a postgres wallet you need to know the url of the postgres server, as well as the account and password to connect.  

For example the following assumes the postres wallet already exists (for example was created by TOB):

```
wallet create tob_holder key storage_type=postgres storage_config={"url":"wallet-db:5432"} storage_credentials={"account":"postgres","password":"mysecretpassword"}
wallet open tob_holder key storage_credentials={"account":"postgres","password":"mysecretpassword"}
```

If you are actually creating a new wallet you also need to provide a postgres admin account:

```
wallet create tob_new key storage_type=postgres storage_config={"url":"wallet-db:5432"} storage_credentials={"account":"postgres","password":"mysecretpassword","admin-account":"postgres","admin-password":"mysecretpassword"}
wallet open tob_new key storage_credentials={"account":"postgres","password":"mysecretpassword"}
```

## Rotating a Wallet's Encryption Keys

To rotate the encryption key you need to specify both "key" and "rekey" when you open the wallet:

```
# enter the old "key" and the new "rekey":
wallet open tob_holder key rekey storage_credentials={"account":"postgres","password":"mysecretpassword"}
wallet close tob_holder

# now use the "rekey" from above as the new "key":
wallet open tob_holder key storage_credentials={"account":"postgres","password":"mysecretpassword"}
```

Note that you are prompted for the "key" and "rekey" values.  Remember the latest value as you need it to open the wallet!  (I.e. the value you enter for "rekey" is the value you need to use for "key" next time you open the wallet.)

## Exporting and Importing a Wallet

Easy peasy - this example exports from Postgres and imports into SQLite:

```
wallet open ... (whatever wallet you want to export)
wallet export export_path=/tmp/wallet_export_file export_key
wallet close ...
```

You create the new wallet on import, so you need to provide all the same info as in "wallet create ...".

For SQLite:

```
wallet import new_wallet key export_path=/tmp/wallet_export_file export_key
```

... but for Postgres:

```
wallet import new_wallet key export_path=/tmp/wallet_export_file export_key storage_config={"url":"wallet-db:5432"} storage_credentials={"account":"postgres","password":"mysecretpassword","admin-account":"postgres","admin-password":"mysecretpassword"}
```

... and you need the admin credentials, because import needs to create a new wallet.
