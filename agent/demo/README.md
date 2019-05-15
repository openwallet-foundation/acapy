# Running the Alice/Faber Pytho demo

To run this demo, first startup a local ledger (e.g. like this:  https://github.com/hyperledger/indy-sdk#1-starting-the-test-pool-on-localhost), and then open up two shell scripts and run:

```
python faber-pg.py <port#>
```

```
python alice-pg.py <port#>
```

Note that alice and faber will each use 5 ports, e.g. if you run ```python faber-pg.py 8020``` if will actually use 
ports 8020 through 8024.

Faber will create and display an invitation; copy this invitation and input at the Alice prompt.

The scripts will then request an option:

faber-pg.py - establishes a connection with Alice, and then provides a menu:

```
                 1 = send credential to Alice
                 2 = send proof request to Alice
                 3 = send a message to Alice
                 x = stop and exit
```

alice-pg.py - once a connection is established, this script provides a menu:

```
                 3 = send a message to Faber
                 x = stop and exit
```

At the Faber prompt, enter "1" to send a credential, and then "2" to request a proof.

You don't need to do anything with Alice - she will automatically receive Credentials and respond to Proofs.

To create the alice/faber wallets using postgres storage, just add the "--postgres" option when running the script.

These scripts run the agent as a sub-process (see the documentation for icatagent) and also publish a rest service to 
receive web hook callbacks from their agent

