# How to Publish a New Version

The code to be published should be at the HEAD of the `main` branch or of an LTS
branch. Make sure that all the PRs to go in the release are merged, and decide
on the release tag. Should it be a release candidate or the final tag, and
should it be a major, minor or patch release, per [semver](https://semver.org/)
rules?

Once ready to do a release, follow these steps:

1. Create a local PR branch from an updated `main` or LTS branch, e.g. `git checkout -b 1.7.0`.
   - For a main branch release update your local `main` branch with the latest changes from the upstream `main` branch before creating the new release branch - e.g. `git fetch upstream;git merge upstream/main main`
   - For an LTS release, you have to check out the latest LTS branch locally. For example, run `git fetch upstream; git checkout 1.3.lts; git merge upstream/1.3.lts --ff-only` for the appropriate LTS branch.

2. See if there are any Document Site `mkdocs` changes needed. Run the script
   `./scripts/prepmkdocs.sh; mkdocs`. Watch the log, noting particularly if
   there are new documentation files that are in the docs folder and not
   referenced in the mkdocs navigation. If there is, update the `mkdocs.yml`
   file as necessary. On completion of the testing, run the script
   `./scripts/prepmkdocs.sh clean` to undo the temporary changes to the docs. Be
   sure to do the last `clean` step -- **DO NOT MERGE THE TEMPORARY DOC
   CHANGES.** For more details see the [Managing the ACA-Py Documentation Site] document.

2. Update the CHANGELOG.md to add the new release.  Only create a new section
   when working on the first release candidate for a new release. When
   transitioning from one release candidate to the next, or to an official
   release, just update the title and date of the change log section.

3. Collect the details of the merged PRs included in this release -- a list of
   PR title, number, link to PR, author's github ID, and a link to the author's
   github account. Do not include `dependabot` PRs. For those, we put a live
   link for the date range of the release (guidance below).

   To generate the list, run `./scripts/genChangeLog.sh YYYY-MM-DD [<branch>]`
   (requires you have [gh] and [jq] installed), with the date the day before the
   last release. The day before is picked to make sure you pick up all of the
   changes. The script generates the list of all PRs merged since the date
   (minus, for a `main` branch runs, dependabot PRs) in the required markdown
   format for the ChangeLog entry. At the end of the list is some markdown for
   putting a link into a `main` branch release for the ChangeLog to see the
   dependabot PRs merged in the release. Assuming you are creating a Release PR,
   the last line of the output is the number of the PR you will be creating
   (unless someone gets another one in before you do).

   **Note**: The output of the script is _roughly_ what you need for the
   ChangeLog, but use your discretion in getting the list right, and making
   sure the dates for the dependabot PRs link is correct. For example, when doing a
   follow up to an RC release, the date range in the dependabot link should
   be the day before the last non-RC release, which won't be generated correctly
   for the non-RC release.

   [gh]: https://github.com/cli/cli
   [jq]: https://jqlang.github.io/jq/download/

   Once you have the list of PRs follow the format of past ChangeLog entries to create a complete entry for the release. After an RC entry has been created, updated it for the next RC or final release -- don't add new entries for the same release. An AI can be used to help generate the ChangeLog entry, but it is important to review the output and make sure it is correct and complete.

4. Check to see if there are any other PRs that should be included in the release.

5. Update the ReadTheDocs in the `/docs` folder by following the instructions in
   the `docs/UpdateRTD.md` file. That will likely add a number of new and modified
   files to the PR. Eliminate all of the errors in the generation process,
   either by mocking external dependencies or by fixing ACA-Py code. If
   necessary, create an issue with the errors and assign it to the appropriate
   developer. Experience has demonstrated to use that documentation generation
   errors should be fixed in the code.

```sh
cd docs; rm -rf generated; sphinx-apidoc -f -M -o  ./generated ../acapy_agent/ $(find ../acapy_agent/ -name '*tests*'); cd ..
cd docs; sphinx-build -b html -a -E -c ./ ./ ./_build; cd ..
```

   Sphinx can be run with docker -- at least the first step.  Here is the command to use:

```sh
cd docs; cp -r ../docker_agent .; rm -rf generated; docker run -it --rm -v .:/docs sphinxdoc/sphinx sphinx-apidoc -f -M -o  ./generated ./acapy_agent/ $(find ./acapy_agent/ -name '*tests*'); rm -rf docker_agent; cd ..
```

   For the build test, the RTD Sphinx theme needs to be added to the docker image, and I've not figured out that yet.

6. Search across the repository for the previous version number and update it
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

7. Regenerate openapi.json and swagger.json by running
   `scripts/generate-open-api-spec` from within the `acapy_agent` folder.

   Command: `cd acapy_agent;../scripts/generate-open-api-spec;cd ..`

   Folders may not be cleaned up by the script, so the following can be run,
   likely with `sudo` -- `rm -rf open-api/.build`. The folder is `.gitignore`d,
   so there is not a danger they will be pushed, even if they are not deleted.

8. Double check all of these steps above, and then submit a PR from the branch.
   Add this new PR to CHANGELOG.md so that all the PRs are included.
   If there are still further changes to be merged, mark the PR as "Draft",
   repeat **ALL** of the steps again, and then mark this PR as ready and then
   wait until it is merged. It's embarrassing when you have to do a whole new
   release just because you missed something silly...I know!

9. Immediately after the PR is merged and if the release is a final release AND
    the latest release AND an LTS release, update the LTS branch to point to
    `main`. Do this ONLY when the current release version is both the latest
    release AND its version has been declared an LTS release. Once a new version
    has been created that has NOT been declared an LTS, the LTS branch will
    extend independent of main.

10. Immediately after the PR is merged, create a new GitHub tag representing the
   version. The tag name and title of the release should be the same as the
   version in
   [pyproject.toml](https://github.com/openwallet-foundation/acapy/tree/main/pyproject.toml).
   Use the "Generate Release Notes" capability to get a sequential listing of
   the PRs in the release, to complement the manually curated Changelog. Verify
   on PyPi that the version is published.

11. New images for the release are automatically published by the GitHubAction
   Workflow: [publish.yml]. The action is triggered when a release is tagged, so
   no manual action is needed. Images are published in the [OpenWallet
   Foundation Package Repository under
   acapy-agent](https://github.com/openwallet-foundation/acapy/pkgs/container/acapy-agent/versions?filters%5Bversion_type%5D=tagged).

   **Image Tagging Strategy:**
   
   Published images are automatically tagged with multiple tags for flexibility:
   
   - **Regular Releases** (e.g., `1.7.0`):
     - `py3.12-1.7.0` - Python version specific tag
     - `1.7.0` - Semantic version tag
     - `1.7` - Major.minor tag (moves to latest patch release)
     - `latest` - Only assigned if this is the highest semantic version
   
   - **Release Candidates** (e.g., `1.7.0rc0`):
     - `py3.12-1.7.0rc0` - Python version specific RC tag
     - `1.7.0rc0` - Semantic version RC tag
     - **Note**: RC releases do NOT receive major.minor (`1.7`) or `latest` tags
   
   The `latest` tag is explicitly managed by comparing semantic versions across all
   releases. It will only be applied to the highest non-RC semantic version. For
   example, if version `0.12.5` is released after `1.3.0`, the `latest` tag will
   remain on `1.3.0` because `1.3.0 > 0.12.5` in semantic version ordering.
   
   **LTS (Long Term Support) Releases:**
   
   LTS versions receive additional tags (e.g., `py3.12-1.6-lts`) that move to the
   latest patch release in that LTS line. LTS versions are configured in
   `.github/lts-versions.txt`. See `.github/LTS-README.md` for more details.

   Additional information about the container image publication process can be
   found in the document [Container Images and Github Actions](docs/deploying/ContainerImagesAndGithubActions.md).

   In addition, the published documentation site [https://aca-py.org] must be
   updated to include the new release via the [publish-docs] GitHub Action.
   Additional information about that process and some related maintenance
   activities that are needed from time to time can be found in the [Managing the ACA-Py Documentation Site] document.

[publish.yml]: https://github.com/openwallet-foundation/acapy/blob/main/.github/workflows/publish.yml

12. When a new release is tagged, create a new branch at the same commit with
    the branch name in the format `docs-v<version>`, for example, `docs-v1.7.0`.
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

13. Perform local testing of an RC release using [ACA-Py
    Plugins](https://github.com/openwallet-foundation/acapy-plugins). Once a
    Release Candidate (RC) has been published, a script in the [ACA-Py
    Plugins](https://github.com/openwallet-foundation/acapy-plugins) repo
    `test_acapy_version.py` can be run locally to test the release artifacts with all
    of the plugins. See the documentation about this in the [ACA-Py Plugins
    README](https://github.com/openwallet-foundation/acapy-plugins/blob/main/README.md#testing-an-aca-py-release-candidate)

14. Update the [ACA-Py Read The Docs site] by logging into Read The Docs
    administration site, building a new "latest" (main branch) and activating
    and building the new release by version ID. Appropriate permissions are
    required to publish the new documentation version.

[ACA-Py Read The Docs site]: https://aries-cloud-agent-python.readthedocs.io/en/latest/
