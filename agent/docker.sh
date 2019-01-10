#!/bin/sh

cd $(dirname $0)

docker build -t indy-cat-test -f Dockerfile.test .. || exit 1

docker run --rm -ti --name indy-cat-runner indy-cat-test