# How to Publish a New Version

0. The code to be published should be in the `master` branch.

1. Update CHANGELOG.md to include details of the closed PRs included in this release.

2. Update the version number listed in [aries_cloudagent/version.py](aries_cloudagent/version.py). The incremented version number should adhere to the [Semantic Versioning Specification](https://semver.org/#semantic-versioning-specification-semver) based on the changes since the last published release.

3. Create a new GitHub release. The tag name and title of the release should be the same as the version in [aries_cloudagent/version.py](aries_cloudagent/version.py). Include the additions to CHANGELOG.md in the release notes.

4. Create a new [distribution package](https://packaging.python.org/glossary/#term-distribution-package) with `python setup.py sdist bdist_wheel`

5. Publish the release to [PyPI](https://pypi.org) using [twine](https://pypi.org/project/twine/) with `twine upload dist/*`
