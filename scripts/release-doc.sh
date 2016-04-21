#!/bin/sh

set -e

# Update gh-pages
git checkout gh-pages
git fetch
git merge

# Update documentation
git rm -r .
cp -r doc/build/* .
git add $(ls doc/build)

# Publish
git commit -m "Update documentation"
git push

git checkout master
