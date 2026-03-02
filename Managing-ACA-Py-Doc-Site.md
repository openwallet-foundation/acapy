# Managing the ACA-Py Documentation Site

The ACA-Py documentation site is a [MkDocs Material] site generated from the
Markdown files in this repository. Whenever the `main` branch is updated or a
release branch is (possibly temporarily) created, the [publish-docs] GitHub
Action is fired, generating and publishing the documentation for the
updated/created branch. The generation process generates the static set of HTML
pages for the version in a folder in the `gh-pages` branch of this repo. The
static pages for each (other than the `main` branch) version are not updated
after creation. From time to time, some "extra" maintenance on the versions are
needed and this document describes those activities.

[MkDocs Material]: https://squidfunk.github.io/mkdocs-material/
[publish-docs]: https://github.com/openwallet-foundation/acapy/blob/main/.github/workflows/publish-docs.yml

## Generation Process

The generation process includes the following steps as part of the GitHub Action
and mkdocs configuration.

When the GitHub Action fires, it runs a container that carries out the following steps:

- Checks out the triggering branch, either `main` or `docs-v<version>` (e.g `docs-v1.5.1`).
- Runs the script [scripts/prepmkdocs.sh], which moves and updates some of the
  markdown files so that they fit into the generated site. See the comments in
  the scripts for details about the copying and editing done via the script. In
  general, the copying of files is to put markdown files in the root folder into
  the `docs` folder, and to update links that need to be changed to work on the
  generated site. This allows us to have links working using the GitHub UI and
  on the generated site.
- Invokes the mkdocs extension `mike` that generates the mkdocs HTML pages and
  then captures and commits them into the `gh-pages` branch of the repository.
  It also adds (if needed) a reference to the new version in the site's
  "versions" dropdown, enabling users to pick the version of the docs they want
  to look at. The process uses the [mkdocs.yml] configuration file in generating
  the site.

[scripts/prepmkdocs.sh]: https://github.com/openwallet-foundation/acapy/blob/main/scripts/prepmkdocs.sh
[mkdocs.yml]: https://github.com/openwallet-foundation/acapy/blob/main/mkdocs.yml

## Preparing for a Release

When preparing for a release (or even just a PR to `main`) you can test the
documentation site on your local clone using the following steps. The steps
assume that you have installed `mkdocs` on your system. Guidance for that can be
found in the [MkDocs Material] documentation.

- Note the files changed in your repository that have not been committed. This
  process will change and then "unchange" files in your local clone. The
  "unchange" may not be perfect, so you want to be sure that no extra changed
  files get into your next commit.
- Run the bash script [scripts/prepmkdocs.sh]. It will change a number of files
  in your local repository.
- Run `mkdocs`. Watch for warnings of missing documents and broken links in the
  startup messages. See the notes below for dealing with those issues.
- Open your browser and browse the site, looking for any issues.
- Update the documents, [mkdocs.yml] and the [scripts/prepmkdocs.sh] as needed,
  repeating the generation process as needed.
- When you are happy run [scripts/prepmkdocs.sh] with the parameter `clean`.
  This should undo the changes done by the script. You should check that there
  no unexpected files changed that you don't want committed into the repo.

If there are missing documents, it may be that they are new Markdown files that
have not yet been added to the [mkdocs.yml] navigation. Update that file to add
the new files, and push the changes to the repository in a pull request. There
are a few files listed below that we don't generate into the documentation site,
and they can be ignored.

- `assets/README.md`
- `design/AnonCredsW3CCompatibility.md`
- `design/UpgradeViaApi.md`
- `features/W3cCredentials.md`

If there are broken links, it is likely because there is a Markdown link that
works using the GitHub UI (e.g. a relative link to a file in the repo) but
doesn't on the generated site. In general there are two ways to fix these:

- Change the link in the Markdown file so that it is a fully qualified URL vs. a
  relative link, so that it works in both the GitHub UI and the generated site.
- Extend the [scripts/prepmkdocs.sh] `sed` commands so that the link differs in
  the GitHub UI and the generated site -- working in both. A pain, but sometimes
  needed...

## Removing RC Releases From the Generated Site

Documentation is added to the site for release candidates (RCs). When those
release candidates are replaced, we want to remove their documentation version
from the documentation site. In the current GitHub Action, the version
documentation is created but never deleted, so the process to remove the
documentation for the RC is manual. It would be nice to create a mechanism in
the GitHub Action to do this automatically, but its not there yet.

To delete the documentation version, do the following:

- In your local fork, checkout the gh-pages: `git checkout -b gh-pages --track
  upstream/gh-pages` (or use whatever local branch name you want)
- Check your `git status` and make sure there are no changes in the branch --
  e.g., new files that shouldn't be added to the `gh-pages` branch. If there are
  any -- delete the files so they are not added.
- Remove the folder for the RC.  For example `rm -rf 1.5.1rc1`
- Edit the `versions.json` file and remove the reference to the RC release in
  the file.
- Push the changes via a PR to the ACA-Py `gh-pages` branch (don't PR them into
  `main`!!).
- Merge the PR and verify (after a few minutes) that the drop down no longer has
  the RC in it.
