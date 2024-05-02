#!/bin/bash

# A script to prep for testing of mkdocs generation, and then to clean up after
# Replicates the file preparation done in the .github/workflows/publish-docs Git Hub Action
# TODO: Move all the prepaanupCalled from the GHA to do all of the work being done there.
#
# Add argument "clean" to undo these changes when just being used for testing.
#    WARNING -- does a `git checkout -- docs` so you will lose any others changes you make!!!

if [[ "$1" == "clean" ]]; then
  rm -f docs/CHANGELOG.md \
        docs/CODE_OF_CONDUCT.md \
        docs/CONTRIBUTING.md \
        docs/MAINTAINERS.md \
        docs/PUBLISHING.md \
        docs/SECURITY.md
    git checkout -- docs
else
    # Copy all of the root level md files into the docs folder for deployment, tweaking the relative paths
    for i in *.md; do sed -e "s#docs/#./#g" $i >docs/$i; done
    # Fix references in DevReadMe.md to moved files
    sed -e "s#\.\./\.\./#../#" docs/features/DevReadMe.md >tmp.md; mv tmp.md docs/features/DevReadMe.md
    # Fix image references in demo documents so they work in GitHub and mkdocs
    for i in docs/demo/AriesOpenAPIDemo.md docs/demo/AliceGetsAPhone.md; do sed -e "s#src=.collateral#src=\"../collateral#" $i >$i.tmp; mv $i.tmp $i; done
    # Cleanup indented bullets in at least the CHANGELOG.md so they look right when published
    for i in docs/CHANGELOG.md; do sed -e 's#^  - #    - #' $i >$i.tmp; mv $i.tmp $i; done
fi
