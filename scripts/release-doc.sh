#!/bin/sh

# TODO: publish at something like docs.meetling.org

set -e

#REPO=git@github.com:meetling/meetling.github.io.git
#BRANCH=master
REPO=$(git config remote.origin.url)
BRANCH=gh-pages
DOCPATH="$PWD/doc/build"
PAGESPATH=/tmp/gh-pages

rm -rf $PAGESPATH
git clone --branch=$BRANCH --single-branch $REPO $PAGESPATH

cd $PAGESPATH

# Update documentation
git rm -r .
cp -r "$DOCPATH"/* .
touch .nojekyll
git add -A

git diff --cached --quiet && exit

# Publish
git commit -m "Update documentation"
git push
