# Multitenancy Support in Alice/Faber

To run either Alice or Faber with multitenancy enabled run with a `--multitenant` flag:

```bash
./run_demo faber --multitenant
```

and:

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

Note that Faber and Alice will use a single Base agent when multitenancy enabled.

Faber boot flow:

* Start Faber in `--multitenant` mode
* Base agent boots and exposes the admin and endpoint
* Faber creates its own wallet and did via Base agent
* Base agent registers the did of Faber as a ENDORSER role
* Faber assigns the did to public and creates an invitation

Alice boot flow:

* Start Alice in `--multitenant` mode
* Alice creates its own wallet via Base agent
* Alice waits input for the invitation of Faber
