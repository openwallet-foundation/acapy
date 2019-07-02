# How to Publish a New Version

1. Update the version number listed in [aries_cloudagent/version.py](aries_cloudagent/version.py). The incremented version number should adhere to the [Semantic Versioning Specification](https://semver.org/#semantic-versioning-specification-semver) based on the changes since the last published release.

2. Create a new GitHub release. The tag name and title of the release should be the same as the version in [aries_cloudagent/version.py](aries_cloudagent/version.py).

3. Create a new [distribution package](https://packaging.python.org/glossary/#term-distribution-package) with `python setup.py sdist bdist_wheel`.

4. Publish the release to [PyPI](https://pypi.org) using [twine](https://pypi.org/project/twine/) with `twine upload dist/*`.
