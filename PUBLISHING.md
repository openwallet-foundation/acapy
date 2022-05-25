# How to Publish a New Version

The code to be published should be in the `main` branch. Make sure that all the PRs to go in the release are
merged, and decide on the release tag. Should it be a release candidate or the final tag, and should it be
a major, minor or patch release, per [semver](https://semver.org/) rules.

Once ready to do a release, create a local branch that includes the following updates:

1. Create a PR branch from an updated `main` branch.

2. Update the CHANGELOG.md to add the new release.  If transitioning for a Release Candidate to the final release for the tag, do not create a new section -- just drop the "RC" designation. Check the date of the new release.

3. Include details of the merged PRs included in this release. General process to follow:

- Gather the set of PRs since the last release and put them into a list. A good tool to use for this is the [github-changelog-generator](https://github.com/github-changelog-generator/github-changelog-generator). Steps:
  - Create a read only GitHub token for your account on this page: [https://github.com/settings/tokens](https://github.com/settings/tokens/new?description=GitHub%20Changelog%20Generator%20token) with a scope of `repo` / `public_repo`.
  - Use a command like the following, adjusting the tag parameters as appropriate. `docker run -it --rm -v "$(pwd)":/usr/local/src/your-app githubchangeloggenerator/github-changelog-generator --user hyperledger --project aries-cloudagent-python --output 0.7.4-rc0.md --since-tag 0.7.3 --future-release 0.7.4-rc0 --release-branch main --token <your-token>`
  - In the generated file, use only the PR list -- we don't include the list of closed issues in the Change Log.
- Organize the list into suitable categories, update (if necessary) the PR description and add notes to clarify the changes. See previous release entries to understand the style -- a format should help developers.
- Add a narrative about the release above the PR that highlights what has gone into the release.

4. Update the ReadTheDocs in the `/docs` folder by following the instructions in the `docs/README.md` file. That will likely add a number of new and modified files to the PR. Eliminate all of the errors in the generation process, either by mocking external dependencies or by fixing ACA-Py code. If necessary, create an issue with the errors and assign it to the appropriate developer. Experience has demonstrated to use that documentation generation errors should be fixed in the code.

5. Update the version number listed in [aries_cloudagent/version.py](aries_cloudagent/version.py) and, prefixed with a "v" in [open-api/openapi.json](open-api/openapi.json) (e.g. "0.7.2" in the version.py file and "v0.7.2" in the openapi.json file). The incremented version number should adhere to the [Semantic Versioning Specification](https://semver.org/#semantic-versioning-specification-semver) based on the changes since the last published release. For Release Candidates, the form of the tag is "0.7.2-rc0".
  
6. An extra search of the repo for the existing tag is recommended to see if there are any other instances of the tag in the repo. If any are found to be required (other than in CHANGELOG.md and the examples in this file, of course), finding a way to not need them is best, but if they are needed, please update this document to note where the tag can be found.

7. Double check all of these steps above, and then submit a PR from the branch. If there are still further changes to be merged, mark the PR as "Draft", repeat **ALL** of the steps again, and then mark this PR as ready and then wait until it is merged.

8. Immediately after it is merged, create a new GitHub tag representing the version. The tag name and title of the release should be the same as the version in [aries_cloudagent/version.py](aries_cloudagent/version.py). Use the "Generate Release Notes" capability to get a sequential listing of the PRs in the release, to complement the manually curated Changelog. Verify on PyPi that the version is published.

9. Publish a new docker container on Docker Hub ([bcgovimages/aries-cloudagent](https://hub.docker.com/r/bcgovimages/aries-cloudagent/)) by following the README.md instructions to create a PR for the release in the repository [https://github.com/bcgov/aries-cloudagent-container](https://github.com/bcgov/aries-cloudagent-container). Appropriate permissions are required to publish the image.

10. Update the ACA-Py Read The Docs site by building the new "latest" (main branch) and activating and building the new release. Appropriate permissions are required to publish the new documentation version.
