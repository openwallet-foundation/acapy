# Multitenancy Support in Alice/Faber

To run either Alice or Faber with multitenancy enabled run with a `--multitenant` flag:

```bash
./run_demo faber --multitenant
```

and/or:

```bash
./run_demo alice --multitenant
```

This will enable a couple of additional options within the demo:

* `W` to create a new wallet (or switch to an existing wallet)
* `4` to create a new invitation (Faber) or accept a new invitation (Alice)

When you create a new wallet, or switch wallet context, you need to create (and accept) a new invitation/connection between the Alice and Faber agents.

For example:

* Start alice and faber in `--multitenant` mode
* Accept the invitation to get to the menus
* In Alice - use the `W` option to create a new wallet
* Use Faber to create a new invitation and then accept that invitation in Alice
* You can now issue credentials from Faber to Alice using the new connection/wallet

TODO - for Faber, the new wallet creation process fails when trying to create a new schema and credential defintion in the new wallet.
