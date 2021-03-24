# Contributing to ansible-vsphere-gos-validation
The "ansible-vsphere-gos-validation" project team welcomes contributions from the community. Before you start working with this project, please read our [Developer Certificate of Origin](https://cla.vmware.com/dco). All contributions to this repository must be signed as described on that page. Your signature certifies that you wrote the patch or have the right to pass it on as an open-source patch.

## Contribution flow
### Creating issues
It's better that each pull requrest corresponding to a filed issue.
* Search the existing issues to see if there is same issue filed already,
* File a new issue if there is no filed issue described the same problem as you meet,
* Or file a new feature request if you want to add a new feature in this project.

### Creating pull requests
This is a rough outline of what a contributor's workflow looks like:
* Fork your own copy of this project to your account and clone it to your computer,
* Create a topic branch from the development branch,
* Make commits of logical units,
* Make sure your commit messages are in the proper format (see below),
* Push your changes to a topic branch in your forked repository,
* Create a pull request.
Example:
```
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY
git remote add upstream https://github.com/vmware/ansible-vsphere-gos-validation.git
git checkout -b my-new-feature master
git commit -a
git push origin my-new-feature
```

### Staying in sync with upstream
When your branch gets out of sync with the master branch, use the following to update:
```
git checkout my-new-feature
git fetch -a
git pull --rebase upstream master
git push --force-with-lease origin my-new-feature
```

### Updating pull requests
If your PR fails to pass CI or needs changes based on code review, you'll most likely want to squash these changes into existing commits.
If your pull request contains a single commit or your changes are related to the most recent commit, you can simply amend the commit.
```
git add .
git commit --amend
git push --force-with-lease origin my-new-feature
```
If you need to squash changes into an earlier commit, you can use:
```
git add .
git commit --fixup <commit>
git rebase -i --autosquash master
git push --force-with-lease origin my-new-feature
```
Add a comment to the PR indicating your new changes are ready to review.

## Code style
### Formatting commit messages
We follow the conventions on [How to Write a Git Commit Message](https://chris.beams.io/posts/git-commit/).
Be sure to include any related GitHub issue references in the commit message. See [GFM syntax](https://guides.github.com/features/mastering-markdown/#GitHub-flavored-markdown) for referencing issues and commits.
