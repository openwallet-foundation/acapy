# Multitenancy Support in Alice/Faber

To run either Alice or Faber with multitenancy enabled run with a `--multitenant` flag:

```bash
./run_demo faber --multitenant
```

and:

```bash
./run_demo alice --multitenant
```

This will enable a multitenancy support, and Faber and Alice will use a single Base agent.

Faber boot flow:

* Start Faber in `--multitenant` mode
* Base agent boots and exposes the admin and endpoint
* Faber creates its own wallet and did via Base agent
* Base agent registers the did of Faber as a ENDORSER role
* Faber assigns the did to public and creates an invitation

Alice boot flow:

* Start Alice in `--multitenant` mode
* Alice creates its own wallet and did via Base agent
* Alice waits input for the invitation of Faber
