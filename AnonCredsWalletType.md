# AnonCreds-Rs Support

A new wallet type has been added to Aca-Py to support the new anoncreds-rs library:

```
--wallet-type askar-anoncreds
```

When Aca-Py is run with this wallet type it will run with an Askar format wallet (and askar libraries) but will use `anoncreds-rs` instead of `credx`.

There is a new package under `aries_cloudagent/anoncreds` with code that supports the new library.  This contains new endpoints for registering schemas and credential definitions.

Within the protocols, there are new `handler` libraries to support the new `anoncreds` format (these are in parallel to the existing `indy` libraries).

The existing `indy` code are in:

```
```

The new `anoncreds` code is in:

```
```


