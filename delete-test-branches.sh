#!/bin/bash

# Delete remote branches
git branch -r | grep "origin/test-branch-" | sed 's/origin\///' | xargs -r -I {} git push origin --delete {}

# Delete local branches
git branch | grep "test-branch-" | xargs -r -I {} git branch -D {}
