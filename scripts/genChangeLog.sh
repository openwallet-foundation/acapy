#!/bin/bash

if ! command -v gh 2>&1 >/dev/null; then
   echo ERROR: This script requires that `gh` needs to be installed to run.
   exit 1
fi

if ! command -v jq 2>&1 >/dev/null; then
   echo ERROR: This script requires that `jq` needs to be installed to run.
   exit 1
fi

if [ $# -eq 0 ]; then
    echo ${0} \<date\> \[\<branch\>\]: Generate a list of PRs to include in the Changelog for a release.
    echo "You must supply the date argument in the format '2024-08-12'"
    echo "The date must be the date of the day before the last ACA-Py release -- to make sure you get all of the relevant PRs."
    echo "The output is the list of non-dependabot PRs, plus some markdown to reference the dependabot PRs"
    echo "The branch argument is optional, and defaults to 'main'."
    exit 1
fi

if [ $# -eq 1 ]; then
    BRANCH=main
else
    BRANCH=$2
fi

gh pr list -S "merged:>${1}"  -L 1000 -B ${BRANCH} --state merged --json number,title,author | \
   jq ' .[] | ["  -",.title,"WwW",.number,"XxX",.number,"YyY",.author.login,"ZzZ",.author.login] | @tsv' | \
   sed -e "s/\\\t/ /g" \
      -e "s/\"//g" \
      -e "s/WwW /\[\\\#/" \
      -e "s# XxX #\\](https://github.com/openwallet-foundation/acapy/pull/#" \
      -e "s/ YyY /) \\[/" \
      -e "s# ZzZ #\\](https://github.com/#" \
      -e "s/$/)/" \
      -e "/app.dependabot/d"
now=$(date +%Y-%m-%d)
echo ""
echo "- Dependabot PRs"
echo "  - [Link to list of Dependabot PRs in this release](https://github.com/openwallet-foundation/acapy/pulls?q=is%3Apr+is%3Amerged+merged%3A${1}..${now}+author%3Aapp%2Fdependabot+)"

echo Here are the latest issues and pull requests. The release PR you are preparing should be one higher than the highest of the numbers listed:
gh issue list -s all -L 1; gh pr ls -s all -L 1
