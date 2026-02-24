# How to Publish a New Version

The code to be published should be in the `main` branch. Make sure that all the PRs to go in the release are
merged, and decide on the release tag. Should it be a release candidate or the final tag, and should it be
a major, minor or patch release, per [semver](https://semver.org/) rules.

Once ready to do a release, create a local branch that includes the following updates:

1. Create a local PR branch from an updated `main` branch, e.g. "1.2.6rc1".

2. See if there are any Document Site `mkdocs` changes needed. Run the script
   `./scripts/prepmkdocs.sh; mkdocs`. Watch the log, noting particularly if
   there are new documentation files that are in the docs folder and not
   referenced in the mkdocs navigation. If there is, update the `mkdocs.yml`
   file as necessary. On completion of the testing, run the script
   `./scripts/prepmkdocs.sh clean` to undo the temporary changes to the docs. Be
   sure to do the last `clean` step -- **DO NOT MERGE THE TEMPORARY DOC
   CHANGES.** For more details see the [Managing the ACA-Py Documentation Site] document.

3. Update the CHANGELOG.md to add the new release.  Only create a new section
   when working on the first release candidate for a new release. When
   transitioning from one release candidate to the next, or to an official
   release, just update the title and date of the change log section.

4. Collect the details of the merged PRs included in this release -- a list of
   PR title, number, link to PR, author's github ID, and a link to the author's
   github account. Do not include `dependabot` PRs. For those, we put a live
   link for the date range of the release (guidance below).
   
   To generate the list, run the `./scripts/genChangeLog.sh` scripts (requires you
   have [gh] and [jq] installed), with the date of the day before the last
   release. The day before is picked to make sure you get all of the changes.
   The script generates the list of all PRs, minus the dependabot ones, merged since
   the last release in the required markdown format for the ChangeLog. At the end
   of the list is some markdown for putting a link into the ChangeLog to see the
   dependabot PRs merged in the release.

   **Note**: The output of the script is _roughly_ what you need for the
   ChangeLog, but use your discretion in getting the list right, and making
   sure the dates for the dependabot PRs is correct. For example, when doing a
   follow up to an RC release, the date range in the dependabot link should
   be the day before the last non-RC release, which won't be generated correctly
   in this release.

   [gh]: https://github.com/cli/cli
   [jq]: https://jqlang.github.io/jq/download/

From the root of the repository folder, run:

```bash
./scripts/genChangeLog.sh <date>
```

Leave off the date argument to get usage information.

The output should look like this -- and what you see in [CHANGELOG.md](CHANGELOG.md):

```text

  - Only change interop testing fork on pull requests [\#3218](https://github.com/openwallet-foundation/acapy/pull/3218) [jamshale](https://github.com/jamshale)
  - Remove the RC from the versions table [\#3213](https://github.com/openwallet-foundation/acapy/pull/3213) [swcurran](https://github.com/swcurran)
  - Feature multikey management [\#3246](https://github.com/openwallet-foundation/acapy/pull/3246) [PatStLouis](https://github.com/PatStLouis)

```

Once you have the list of PRs:

- Organize the list into suitable categories in the [CHANGELOG.md](CHANGELOG.md) file, update (if necessary) the PR title and add notes to clarify the changes. See previous release entries to understand the style -- a format that should help developers.
- Add a narrative about the release above the PR that highlights what has gone into the release.
- To cover the `dependabot` PRs without listing them all, add to the end of the
  categorized list of PRs the two `dependabot` lines of the script output (after the list of PRs). The text will look like this:

```text
- Dependabot PRs
  - [List of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A2024-08-16..2024-09-16+author%3Aapp%2Fdependabot+)
```

- Check the dates in the `dependabot` URL to make sure the full period between the previous non-RC release to the date of the non-RC release you are preparing.
- Include a PR in the list for this soon-to-be PR, initially with the "next to be issued" number for PRs/Issues. At the end output of the script is the highest numbered PR and issue. Your PR will be one higher than the highest of those two numbers. Note that you still might have to correct the number after you create the PR if someone sneaks an issue or PR in before you submit your PR.

5. Check to see if there are any other PRs that should be included in the release.

6. Update the ReadTheDocs in the `/docs` folder by following the instructions in
   the `docs/UpdateRTD.md` file. That will likely add a number of new and modified
   files to the PR. Eliminate all of the errors in the generation process,
   either by mocking external dependencies or by fixing ACA-Py code. If
   necessary, create an issue with the errors and assign it to the appropriate
   developer. Experience has demonstrated to use that documentation generation
   errors should be fixed in the code.

7. Search across the repository for the previous version number and update it
   everywhere that makes sense. The CHANGELOG.md entry for the previous release
   is a likely exception, and the `pyproject.toml` in the root **MUST** be
   updated. You can skip (although it won't hurt) to update the files in the
   `open-api` folder as they will be automagically updated by the next step in
   publishing. The incremented version number **MUST** adhere to the [Semantic
   Versioning
   Specification](https://semver.org/#semantic-versioning-specification-semver)
   based on the changes since the last published release. For Release
   Candidates, the form of the tag is "0.11.0rc2". As of release `0.11.0` we
   have dropped the previously used `-` in the release candidate version string
   to better follow the semver rules.

8. Regenerate openapi.json and swagger.json by running
   `scripts/generate-open-api-spec` from within the `acapy_agent` folder.

   Command: `cd acapy_agent;../scripts/generate-open-api-spec;cd ..`

   Folders may not be cleaned up by the script, so the following can be run, likely with `sudo` -- `rm -rf open-api/.build`. The folder is `.gitignore`d, so there is not a danger they will be pushed, even if they are not deleted.

9.  Double check all of these steps above, and then submit a PR from the branch.
   Add this new PR to CHANGELOG.md so that all the PRs are included.
   If there are still further changes to be merged, mark the PR as "Draft",
   repeat **ALL** of the steps again, and then mark this PR as ready and then
   wait until it is merged. It's embarrassing when you have to do a whole new
   release just because you missed something silly...I know!

10.    Immediately after it is merged, create a new GitHub tag representing the
   version. The tag name and title of the release should be the same as the
   version in [pyproject.toml](https://github.com/openwallet-foundation/acapy/tree/main/pyproject.toml). Use
   the "Generate Release Notes" capability to get a sequential listing of the
   PRs in the release, to complement the manually curated Changelog. Verify on
   PyPi that the version is published.

11.     New images for the release are automatically published by the GitHubAction
   Workflows: [publish.yml] and [publish-indy.yml]. The actions are triggered
   when a release is tagged, so no manual action is needed. The images are
   published in the [OpenWallet Foundation Package Repository under
   acapy](https://github.com/openwallet-foundation/packages?repo_name=acapy)
   and a link to the packages added to the repositories main page (under
   "Packages").

   Additional information about the container image publication process can be
   found in the document [Container Images and Github Actions](docs/deploying/ContainerImagesAndGithubActions.md).

   In addition, the published documentation site [https://aca-py.org] should be automatically updated to include the new release via the [publish-docs] GitHub Action.
   Additional information about that process and some related maintenance activities that are needed from time to time can be found in the [Updating the ACA-Py Documentation Site] document.

[publish.yml]: https://github.com/openwallet-foundation/acapy/blob/main/.github/workflows/publish.yml
[publish-indy.yml]: https://github.com/openwallet-foundation/acapy/blob/main/.github/workflows/publish-indy.yml

12.   When a new release is tagged, create a new branch at the same commit with
    the branch name in the format `docs-v<version>`, for example, `docs-v1.2.6`.
    The creation of the branch triggers the execution of the [publish-docs]
    GitHub Action which generates the documentation for the new release,
    publishing it at [https://aca-py.org]. The GitHub Action also executes when
    the `main` branch is updated via a merge, publishing an update to the `main`
    branch documentation. Additional information about that documentation
    publishing process and some related maintenance activities that are needed
    from time to time can be found in the [Managing the ACA-Py Documentation Site] document.

[publish-docs]: https://github.com/openwallet-foundation/acapy/blob/main/.github/workflows/publish-docs.yml
[Managing the ACA-Py Documentation Site]: Managing-ACA-Py-Doc-Site.md
[https://aca-py.org]: https://aca-py.org

13.  Update the [ACA-Py Read The Docs site] by logging into Read The Docs
    administration site, building a new "latest" (main branch) and activating
    and building the new release by version ID. Appropriate permissions are
    required to publish the new documentation version.

[ACA-Py Read The Docs site]: https://aries-cloud-agent-python.readthedocs.io/en/latest/
