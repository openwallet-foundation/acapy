# How to Publish a New Version

The code to be published should be in the `main` branch. Make sure that all the PRs to go in the release are
merged, and decide on the release tag. Should it be a release candidate or the final tag, and should it be
a major, minor or patch release, per [semver](https://semver.org/) rules.

Once ready to do a release, create a PR that includes the following updates:

1. Update the CHANGELOG.md to add the new release.  If transitioning for a Release Candidate to the final release for the tag, do not create a new section -- just drop the "RC" designation.

2. include details of the closed PRs included in this release. General process to follow:

- Gather the set of PRs since the last release and put them into a list.
  - An example query to use to get the list of PRs is: [https://github.com/hyperledger/aries-cloudagent-python/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated+merged%3A%3E2021-11-15](https://github.com/hyperledger/aries-cloudagent-python/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated+merged%3A%3E2021-11-15), where the date at the end is the date of the previous release.
  - Organize the list into suitable categories, update (if necessary) the PR description and add notes to clarify the changes.
  - Add a link to each PR on the PR number.
    - A regular expression you can use in VS Code to add the links to the list (assuming each line ends with the PR number) is `#([0-9]*)` (find) and `[#$1](https://github.com/hyperledger/aries-cloudagent-python/pull/$1)` (replace). Use regular expressions in the search, highlight the list and choose "Find in Selection" before replacing.
  - Add a narrative about the release above the PR that highlights what has gone into the release.

3. Update the ReadTheDocs in the `/docs` folder by following the instructions in the `docs/README.md` file. That will likely add a number of new and modified files to the PR. Eliminate all of the errors in the generation process, either by mocking external dependencies or by fixing ACA-Py code. If necessary, create an issue with the errors and assign it to the appropriate developer. Experience has demonstrated to use that documentation generation errors should be fixed in the code.

4. Update the version number listed in [aries_cloudagent/version.py](aries_cloudagent/version.py). The incremented version number should adhere to the [Semantic Versioning Specification](https://semver.org/#semantic-versioning-specification-semver) based on the changes since the last published release.

5. Create a new GitHub release. The tag name and title of the release should be the same as the version in [aries_cloudagent/version.py](aries_cloudagent/version.py). Include the additions to CHANGELOG.md in the release notes.

6. Publish a new docker container on Docker Hub ([bcgovimages/aries-cloudagent](https://hub.docker.com/r/bcgovimages/aries-cloudagent/)) by following the instructions to create a PR for the release in the repository [https://github.com/bcgov/aries-cloudagent-container](https://github.com/bcgov/aries-cloudagent-container).
