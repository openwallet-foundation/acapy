# How to Publish a New Version

The code to be published should be in the `main` branch. Make sure that all the PRs to go in the release are
merged, and decide on the release tag. Should it be a release candidate or the final tag, and should it be
a major, minor or patch release, per [semver](https://semver.org/) rules.

Once ready to do a release, create a local branch that includes the following updates:

1. Create a PR branch from an updated `main` branch.

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

4. Collect the details of the merged PRs included in this release -- a list of PR
   title, number, link to PR, author's github ID, and a link to the author's
   github account. Gathering that data can be painful. Here are is the current
   easiest way to do this -- using [OpenAI ChatGPT]:

> Prepare the following ChatGPT request. Don't hit enter yet--you have to add the data.
>
> `Generate from this the github pull request number, the github id of the author and the title of the pull request in a tab-delimited list`
>
> Get a list of the merged PRs since the last release by displaying the PR list in
> the GitHub UI, highlighting/copying the PRs and pasting them below the ChatGPT
> request, one page after another. Hit `<Enter>`, let the AI magic work, and you
> should have a list of the PRs in a nice table with a `Copy` link that you should click.
> 
> Once you have that, open this [Google Sheet] and highlight the `A1` cell and
> paste in the ChatGPT data. A formula in column `E` will have the properly
> formatted changelog entries. Double check the list with the GitHub UI to make
> sure that ChatGPT isn't messing with you and you have the needed data.

[OpenAI ChatGPT]: https://chat.openai.com
[Google Sheet]: https://docs.google.com/spreadsheets/d/1gIjPirZ42g5eM-JBtVt8xN5Jm0PQuEv91a8woRAuDEg/edit?usp=sharing

Once you have the list of PRs:

- Organize the list into suitable categories, update (if necessary) the PR description and add notes to clarify the changes. See previous release entries to understand the style -- a format that should help developers.
- Add a narrative about the release above the PR that highlights what has gone into the release.

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
   `scripts/generate-open-api-spec` from within the `aries_cloudagent` folder.

   Command: `cd aries_cloudagent;../scripts/generate-open-api-spec;cd ..`

9.  Double check all of these steps above, and then submit a PR from the branch.
   Add this new PR to CHANGELOG.md so that all the PRs are included.
   If there are still further changes to be merged, mark the PR as "Draft",
   repeat **ALL** of the steps again, and then mark this PR as ready and then
   wait until it is merged. It's embarrassing when you have to do a whole new
   release just because you missed something silly...I know!

10. Immediately after it is merged, create a new GitHub tag representing the
   version. The tag name and title of the release should be the same as the
   version in [pyproject.toml](https://github.com/hyperledger/aries-cloudagent-python/tree/main/pyproject.toml). Use
   the "Generate Release Notes" capability to get a sequential listing of the
   PRs in the release, to complement the manually curated Changelog. Verify on
   PyPi that the version is published.

11.  New images for the release are automatically published by the GitHubAction
   Workflows: [publish.yml] and [publish-indy.yml]. The actions are triggered
   when a release is tagged, so no manual action is needed. The images are
   published in the [Hyperledger Package Repository under
   aries-cloudagent-python](https://github.com/orgs/hyperledger/packages?repo_name=aries-cloudagent-python)
   and a link to the packages added to the repositories main page (under
   "Packages").

   Additional information about the container image publication process can be
   found in the document [Container Images and Github Actions](docs/deploying/ContainerImagesAndGithubActions.md).

   In addition, the published documentation site [https://aca-py.org] should be automatically updated to include the new release via the [publish-docs] GitHub Action.
   Additional information about that process and some related maintainance activities that are needed from time to time can be found in the [Updating the ACA-Py Documentation Site] document.

[publish.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish.yml
[publish-indy.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish-indy.yml

1.  When a new release is tagged, create a new branch at the same commit with
    the branch name in the format `docs-v<version>`, for example, `docs-v1.0.0`.
    The creation of the branch triggers the execution of the [publish-docs]
    GitHub Action which generates the documentation for the new release,
    publishing it at [https://aca-py.org]. The GitHub Action also executes when
    the `main` branch is updated via a merge, publishing an update to the `main`
    branch documentation. Additional information about that documentation
    publishing process and some related maintenance activities that are needed
    from time to time can be found in the [Managing the ACA-Py Documentation Site] document.

[publish-docs]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish-docs.yml
[Managing the ACA-Py Documentation Site]: Managing-ACA-Py-Doc-Site.md
[https://aca-py.org]: https://aca-py.org

13.  Update the [ACA-Py Read The Docs site] by logging into Read The Docs
    administration site, building a new "latest" (main branch) and activating
    and building the new release by version ID. Appropriate permissions are
    required to publish the new documentation version.

[ACA-Py Read The Docs site]: https://aries-cloud-agent-python.readthedocs.io/en/latest/
