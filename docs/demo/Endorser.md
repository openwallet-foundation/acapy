# Endorser Demo

There are two ways to run the alice/faber demo with endorser support enabled.

## Run Faber as an Author, with a dedicated Endorser agent

This approach runs Faber as an un-privileged agent, and starts a dedicated Endorser Agent in a sub-process (an instance of ACA-Py) to endorse Faber's transactions.

Start a VON Network instance and a Tails server:

- Following the [Building and Starting](https://github.com/bcgov/von-network/blob/main/docs/UsingVONNetwork.md#building-and-starting) section of the VON Network Tutorial to get ledger started. You can leave off the `--logs` option if you want to use the same terminal for running both VON Network and the Tails server. When you are finished with VON Network, follow the [Stopping And Removing a VON Network](https://github.com/bcgov/von-network/blob/main/docs/UsingVONNetwork.md#stopping-and-removing-a-von-network) instructions.
- Run an AnonCreds revocation registry tails server in order to support revocation by following the instructions in the [Alice gets a Phone](https://github.com/hyperledger/aries-cloudagent-python/blob/master/demo/AliceGetsAPhone.md#run-an-instance-of-indy-tails-server) demo.

Start up Faber as Author (note the tails file size override, to allow testing of the revocation registry roll-over):

```bash
TAILS_FILE_COUNT=5 ./run_demo faber --endorser-role author --revocation
```

Start up Alice as normal:

```bash
./run_demo alice
```

You can run all of Faber's functions as normal - if you watch the console you will see that all ledger operations go through the endorser workflow.

If you issue more than 5 credentials, you will see Faber creating a new revocation registry (encluding endorser operations).


## Run Alice as an Author and Faber as an Endorser

This approach sets up the endorser roles to allow manual testing using the agents' swagger pages:

- Faber runs as an Endorser (all of Faber's functions - issue credential, request proof, etc.) run normally, since Faber has ledger write access
- Alice starts up with a DID aith Author privileges (no ledger write access) and Faber is setup as Alice's Endorser

Start a VON Network and a Tails server using the instructions above.

Start up Faber as Endorser:

```bash
TAILS_FILE_COUNT=5 ./run_demo faber --endorser-role endorser --revocation
```

Start up Alice as Author:

```bash
TAILS_FILE_COUNT=5 ./run_demo alice --endorser-role author --revocation
```

Copy the invitation from Faber to Alice to complete the connection.

Then in the Alice shell, select option "D" and copy Faber's DID (it is the DID displayed on faber agent startup).

This starts up the ACA-Py agents with the endorser role set (via the new command-line args) and sets up the connection between the 2 agents with appropriate configuration.

Then, in the [Alice swagger page](http://localhost:8031) you can create a schema and cred def, and all the endorser steps will happen automatically.  You don't need to specify a connection id or explicitly request endorsement (ACA-Py does it all automatically based on the startup args).

If you check the endorser transaction records in either [Alice](http://localhost:8031) or [Faber](http://localhost:8021) you can see that the endorser protocol executes automatically and the appropriate endorsements were endorsed before writing the transactions to the ledger.
