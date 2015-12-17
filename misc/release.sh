#!/bin/sh

set -e

FEATURE=$1
VERSION=$2

# Configuration
VERSIONFILE=doc/conf.py
VERSIONSUBST="s/^\(version = release = \).*/\1'$VERSION'/"
CHECK="python3 -m unittest discover"

if [ ! -f .git/MERGE_HEAD ]; then
    # Update master
    git checkout master
    git fetch
    git merge

    # Merge (cancel on conflict)
    git merge --no-ff --no-commit "$FEATURE"
fi

if [ -f .git/MERGE_HEAD ]; then
    # Bump version
    cp "$VERSIONFILE" /tmp/versionfile && sed "$VERSIONSUBST" /tmp/versionfile > "$VERSIONFILE"
    git add "$VERSIONFILE"

    # Run checks (cancel on failure)
    $CHECK

    # Publish
    git commit
    git tag "$VERSION"
    git push origin master "$VERSION"

    # Clean up
    git branch -d "$FEATURE"
fi
