# BBS Signatures Support

ACA-Py has supported BBS Signatures for some time. However, the dependency that is used (`bbs`) does not support the ARM architecture, and its inclusion in the default ACA-Py artifacts mean that developers using ARM-based hardware (such as Apple M1 Macs or later) cannot run ACA-Py "out-of-the-box". We feel that providing a better developer experience by supporting the ARM architecture is more important than BBS Signature support at this time. As such, we have removed the BBS dependency from the base ACA-Py artifacts and made it an add-on that those using ACA-Py with BBS must take extra steps to build their own artifacts. This file describes how to do those extra steps.

Regarding future support for BBS Signatures in ACA-Py. There is currently a lot of work going on in developing implementations and BBS-based Verifiable Credential standards. However, at the time of this release, there is not an obvious approach to an implementation to use in ACA-Py that includes ARM support. As a result, we will hold off on updating the BBS Signatures support in ACA-Py until the standards and path forward clarify. In the meantime, maintainers of ACA-Py plan to continue to do all we can to push for newer and better ZKP-based Verifiable Credential standards.

If you require BBS for your deployment an optional "extended" ACA-Py image has been released (`aries-cloudagent-bbs`) that includes BBS, with the caveat that it will very likely not install on ARM architecture.

## Development and Testing

### Developer setup

If you are a contributor or are developing using a local build of ACA-Py and need BBS, the easiest way to include it is to install the optional dependency `bbs` with `poetry` (again with the caveat that it will very likely not install on ARM architecture). The `--all-extras` flag will install the `bbs` optional dependency in ACA-Py:

```shell
poetry install --all-extras
```

### Testing

WARNNG: if you do NOT have `bbs` installed you should exclude the BBS specific integration tests from running with the tag `~@BBS` otherwise they will fail:

```shell
./run_bdd -t ~@BBS
```

See the [Unit](../testing/UnitTests.md) and [Integration](../testing/BDDTests.md) testing docs for more information on how to run tests.
