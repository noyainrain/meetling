#!/bin/sh

set -e

# Update gh-pages
git checkout gh-pages
git fetch
git merge

# Update documentation
git rm -r .
cp -r doc/build/* .
touch .nojekyll
git add $(ls doc/build) .nojekyll

# Publish
git commit -m "Update documentation"
git push

git checkout master
