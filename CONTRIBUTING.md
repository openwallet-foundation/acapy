## How to contribute

You are encouraged to contribute to the repository by **forking and submitting a pull request**.

For significant changes, please open an issue first to discuss the proposed changes to avoid re-work.

(If you are new to GitHub, you might start with a [basic tutorial](https://help.github.com/articles/set-up-git) and check out a more detailed guide to [pull requests](https://help.github.com/articles/using-pull-requests/).)

Pull requests will be evaluated by the repository guardians on a schedule and if deemed beneficial will be committed to the `main` branch. Pull requests should have a descriptive name, include an summary of all changes made in the pull request description, and include unit tests that provide good coverage of the feature or fix. A Continuous Integration (CI) pipeline is executed on all PRs before review and contributors are expected to address all CI issues identified. Where appropriate, PRs that impact the
end-user and developer demos in the repo should include updates or extensions to those demos to cover the new capabilities.

If you would like to propose a significant change, please open an issue first to discuss the work with the community.

Contributions are made pursuant to the Developer's Certificate of Origin, available at [https://developercertificate.org](https://developercertificate.org), and licensed under the Apache License, version 2.0 (Apache-2.0).

## Development Tools

### Pre-commit

A configuration for [pre-commit](https://pre-commit.com/) is included in this repository. This is an optional tool to help contributors commit code that follows the formatting requirements enforced by the CI pipeline. Additionally, it can be used to help contributors write descriptive commit messages that can be parsed by changelog generators.

On each commit, pre-commit hooks will run that verify the committed code complies with flake8 and is formatted with black. To install the flake8 and black checks:

```
$ pre-commit install
```

To install the commit message linter:

```
$ pre-commit install --hook-type commit-msg
```
