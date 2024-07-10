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
   `./scripts/prepmkdocs clean` to undo the temporary changes to the docs. Be
   sure to do the last `clean` step -- **DO NOT MERGE THE TEMPORARY DOC
   CHANGES.**

3. Update the CHANGELOG.md to add the new release.  Only create a new section when working on the first release candidate for a new release. When transitioning from one release candidate to the next, or to an official release, just update the title and date of the change log section.

4. Include details of the merged PRs included in this release. General process to follow:

- Gather the set of PRs since the last release and put them into a list. A good
  tool to use for this is the
  [github-changelog-generator](https://github.com/github-changelog-generator/github-changelog-generator).
  Steps:
  - Create a read only GitHub token for your account on this page:
    [https://github.com/settings/tokens](https://github.com/settings/tokens/new?description=GitHub%20Changelog%20Generator%20token)
    with a scope of `repo` / `public_repo`.
  - Use a command like the following, adjusting the tag parameters as
    appropriate. `docker run -it --rm -v "$(pwd)":/usr/local/src/your-app
    githubchangeloggenerator/github-changelog-generator --user hyperledger
    --project aries-cloudagent-python --output 0.11.0rc2.md --since-tag 0.10.4
    --future-release 0.11.1rc2 --release-branch main --token <your-token>`
  - In the generated file, use only the PR list -- we don't include the list of
    closed issues in the Change Log.

In some cases, the approach above fails because of too many API calls. An
alternate approach to getting the list of PRs in the right format is to use [OpenAI ChatGPT].

Prepare the following ChatGPT request. Don't hit enter yet--you have to add the data.

`Generate from this the github pull request number, the github id of the author and the title of the pull request in a tab-delimited list`

Get a list of the merged PRs since the last release by displaying the PR list in
the GitHub UI, highlighting/copying the PRs and pasting them below the ChatGPT
request, one page after another. Hit `<Enter>`, let the AI magic work, and you
should have a list of the PRs in a nice table with a `Copy` link that you should click.

Once you have that, open this [Google Sheet] and highlight the `A1` cell and
paste in the ChatGPT data. A formula in column `E` will have the properly
formatted changelog entries. Double check the list with the GitHub UI to make
sure that ChatGPT isn't messing with you and you have the needed data.

[OpenAI ChatGPT]: https://chat.openai.com
[Google Sheet]: https://docs.google.com/spreadsheets/d/1gIjPirZ42g5eM-JBtVt8xN5Jm0PQuEv91a8woRAuDEg/edit?usp=sharing

If using ChatGPT doesn't appeal to you, try this scary `sed`/command line approach:

- Put the following commands into a file called `changelog.sed`

``` bash
/Approved/d
/updated /d
/^$/d
/^ [0-9]/d
s/was merged.*//
/^@/d
s# by \(.*\) # [\1](https://github.com/\1)#
s/^ //
s#  \#\([0-9]*\)# [\#\1](https://github.com/hyperledger/aries-cloudagent-python/pull/\1) #
s/  / /g
/^Version/d
/tasks done/d
s/^/- /
```

- Navigate in your browser to the paged list of PRs merged since the last
  release (using in the GitHub UI a filter such as `is:pr is:merged sort:updated
  merged:>2022-04-07`) and for each page, highlight, and copy the text
  of only the list of PRs on the page to use in the following step.
- For each page, run the command
  `sed -e :a -e '$!N;s/\n#/ #/;ta' -e 'P;D' <<EOF | sed -f changelog.sed`,
  paste in the copied text and then type `EOF`.
  Redirect the output to a file, appending each page of output to the file.
  - The first `sed` command in the pipeline merges the PR title and PR number
    plus author lines onto a single line. The commands in the `changelog.sed`
    file just clean up the data, removing unwanted lines, etc.
- At the end of that process, you should have a list of all of the PRs in a form you can
  use in the CHANGELOG.md file.
- To verify you have right number of PRs, you can do a `wc` of the file and there
  should be one line per PR. You should scan the file as well, looking for
  anomalies, such as missing `\`s before `#` characters. It's a pretty ugly process.
  - Using a `curl` command and the GitHub API is probably a much better and more
  robust way to do this, but this was quick and dirty...

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
   `../scripts/generate-open-api-spec` from within the `aries_cloudagent` folder.

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

11. New images for the release are automatically published by the GitHubAction
   Workflows: [publish.yml] and [publish-indy.yml]. The actions are triggered
   when a release is tagged, so no manual action is needed. The images are
   published in the [Hyperledger Package Repository under
   aries-cloudagent-python](https://github.com/orgs/hyperledger/packages?repo_name=aries-cloudagent-python)
   and a link to the packages added to the repositories main page (under
   "Packages").

   Additional information about the container image publication process can be
   found in the document [Container Images and Github Actions](docs/deploying/ContainerImagesAndGithubActions.md).

[publish.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish.yml
[publish-indy.yml]: https://github.com/hyperledger/aries-cloudagent-python/blob/main/.github/workflows/publish-indy.yml

12. Update the ACA-Py Read The Docs site by building the new "latest" (main
    branch) and activating and building the new release. Appropriate permissions
    are required to publish the new documentation version.

13. Update the [https://aca-py.org] website with the latest documentation by
    creating a PR and tag of the latest documentation from this site. Details
    are provided in the [aries-acapy-docs] repository.

[https://aca-py.org]: https://aca-py.org
[aries-acapy-docs]: https://github.com/hyperledger/aries-acapy-docs
