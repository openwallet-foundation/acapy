# Mkdocs Overrides

This folder contains any overrides for the mkdocs docs publishing. Most notably,
the `base.html` file that puts a banner on the screen for all versions of the
docs other than the main branch. The `base.html` file is generated on publishing
the docs (in the publishing GitHub Action) -- and does not exist in the main branch.
