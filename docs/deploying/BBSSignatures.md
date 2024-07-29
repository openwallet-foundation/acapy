# BBS+ Signatures Support

ACA-Py includes support for BBS+ Signatures out of the box through an optional dependency, however the implementation for it is out of date and does not currently support ARM (aarch64 or arm64) architecture (e.g. Apple devices with M1 chips or above).

The base release images of ACA-Py exclude the installation of the `bbs` library to maintain widespread support accross various architectures.

If you require BBS+ for your deployment an optional "extended" ACA-Py image has been released (`aries-cloudagent-bbs`) that includes BBS+, with the caveat that it may not successfully install on ARM architecture.

## Development and Testing

### Developer setup

If you are a contributor or are developing using a local build of ACA-Py and need BBS+, the easiest way to include `bbs` is to install it with `poetry` (again with the caveat that it may not successfully install on ARM Architecture). The `--all-extras` flag will install all of `askar`, `bbs` and `didcommv2`:

```shell
poetry install --all-extras
```

### Testing

WARNNG: if you do NOT have `bbs` installed you should exclude the BBS+ specific integration tests from running with the tag `~@BBS` otherwise they will fail:

```shell
./run_bdd -t ~@BBS
```

See the [Unit](../testing/UnitTests.md) and [Integration](../testing/INTEGRATION-TESTS.md) testing docs for more information on how to run tests.
