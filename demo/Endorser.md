# Endorser Demo

The demo is in an "interim" state right now, endorser support is added but not "fully added".  The following is how it works now (sets up the endorser roles to allow manual testing using the swagger page) but will be updated in the future once the Endorser support in aca-py is finalized.

Run the following in 2 separate shells (make sure you are running von-network and the tails server first):

```bash
./run_demo faber --endorser-role endorser --revocation
```

```bash
./run_demo alice --endorser-role author --revocation
```

Copy the invitation from faber to alice to complete the connection.

Then in the alice shell, select option "D" and copy faber's DID to alice (it is the DID displayed on faber agent startup).

This starts up the aca-py agents with the endorser role set (via the new command-line args) and sets up the connection between the 2 agents with appropriate configuration.

Then, in the [alice swagger page](http://localhost:8031) you can create a schema and cred def, and all the endorser steps will happen automatically.  You don't need to specify a connection id or explicitly request endorsement (aca-py does it all automatically based on the startup args).

If you check the endorser transaction records in either [alice](http://localhost:8031) or [faber](http://localhost:8021) you can see that the endorser protocol executed automatically and the appropriate endorsements were endorsed before writing the transactions to the ledger.
