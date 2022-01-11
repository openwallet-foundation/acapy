# How to Publish a New Version

The code to be published should be in the `main` branch. Make sure that all the PRs to go in the release are
merged, and decide on the release tag. Should it be a release candidate or the final tag, and should it be
a major, minor or patch release, per [semver](https://semver.org/) rules.

Once ready to do a release, create a local branch that includes the following updates:

1. Update the CHANGELOG.md to add the new release.  If transitioning for a Release Candidate to the final release for the tag, do not create a new section -- just drop the "RC" designation. Check the date of the new release.

2. Include details of the merged PRs included in this release. General process to follow:

- Gather the set of PRs since the last release and put them into a list.
  - An example query to use to get the list of PRs is: [https://github.com/hyperledger/aries-cloudagent-python/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated+merged%3A%3E2021-11-15](https://github.com/hyperledger/aries-cloudagent-python/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated+merged%3A%3E2021-11-15), where the date at the end is the date of the previous release.
  - Organize the list into suitable categories, update (if necessary) the PR description and add notes to clarify the changes.
  - Add a link to each PR on the PR number.
    - A regular expression you can use in VS Code to add the links to the list (assuming each line ends with the PR number) is `#([0-9]*)` (find) and `[#$1](https://github.com/hyperledger/aries-cloudagent-python/pull/$1)` (replace). Use regular expressions in the search, highlight the list and choose "Find in Selection" before replacing.
  - Add a narrative about the release above the PR that highlights what has gone into the release.

3. Update the ReadTheDocs in the `/docs` folder by following the instructions in the `docs/README.md` file. That will likely add a number of new and modified files to the PR. Eliminate all of the errors in the generation process, either by mocking external dependencies or by fixing ACA-Py code. If necessary, create an issue with the errors and assign it to the appropriate developer. Experience has demonstrated to use that documentation generation errors should be fixed in the code.

4. Update the version number listed in [aries_cloudagent/version.py](aries_cloudagent/version.py) and, prefixed with a "v" in [open-api/openapi.json](open-api/openapi.json) (e.g. "0.7.2" in the version.py file and "v0.7.2" in the openapi.json file). The incremented version number should adhere to the [Semantic Versioning Specification](https://semver.org/#semantic-versioning-specification-semver) based on the changes since the last published release. For Release Candidates, the form of the tag is "0.7.2-rc0".
  
5. An extra search of the repo for the existing tag is recommended to see if there are any other instances of the tag in the repo. If any are found to be required, finding a way to not need them is best, but if they are needed, please update this document to note where the tag can be found.

6. Double check all of these steps above, and then create a PR from the branch. If there are still further changes to be merged, mark the PR as "Draft", repeat **ALL** of the steps again, and then mark this PR as ready.

7. Create a new GitHub tag representing the version. The tag name and title of the release should be the same as the version in [aries_cloudagent/version.py](aries_cloudagent/version.py). Use the "Generate Release Notes" capability to get a sequential listing of the PRs in the release, to complement the manually created Changelog. Verify on PyPi that the version is published.

8. Publish a new docker container on Docker Hub ([bcgovimages/aries-cloudagent](https://hub.docker.com/r/bcgovimages/aries-cloudagent/)) by following the README.md instructions to create a PR for the release in the repository [https://github.com/bcgov/aries-cloudagent-container](https://github.com/bcgov/aries-cloudagent-container). Appropriate permissions are required to publish the image.

9. Update the ACA-Py Read The Docs site by building the new "latest" (main branch) and activating and building the new release. Appropriate permissions are required to publish the new documentation version.
