This Git cheatsheet summarizes core commands and workflows from the [tutorial](https://www.youtube.com/watch?v=mAFoROnOfHs).

## Setup Commands

- `git --version`: Check Git installation and version.
- `git config --global user.email "your.email@example.com"`: Set global email for commits.
- `git config --global user.name "Your Name"`: Set global name for commits.
- `git init`: Initialize a new local repository in current directory, creating .git folder.
- `git clone <URL>`: Clone a remote repository to local machine.

## Status and Log

- `git status`: View modified, staged, unstaged, and untracked files.
- `git log`: Show full commit history with details.
- `git log --oneline`: Compact commit log with shortened IDs.

## Staging Changes

- `git add .`: Stage all changes in current directory and subdirs.
- `git add -A` or `git add --all`: Stage all changes (new, modified, deleted) in repo.
- `git add *`: Stage new/modified files (excludes deleted).
- `git add <file>`: Stage specific file, e.g., `git add 1.txt`.
- `git add *.txt`: Stage files by extension.
- `git reset`: Unstage all changes back to working directory.

## Commits

- `git commit -m "Message"`: Commit staged changes with message.
- `git reset HEAD~1`: Undo last commit (soft reset).

## Branches

- `git branch`: List branches (* marks current).
- `git branch <name>`: Create new branch from current.
- `git checkout <branch>`: Switch to branch.
- `git checkout <commit-ID>`: Switch to specific commit (detached HEAD).

## Merging

- `git merge <branch>`: Merge branch into current; resolve conflicts manually if needed.

## Remote Operations

- `git push origin <branch>`: Push local branch to remote, e.g., `git push origin main`.
- `git fetch`: Download remote changes without merging.
- `git pull`: Fetch and merge remote changes (`git fetch + git merge`).

## File Removal

- `git rm <file>`: Delete and stage file.
- `git rm -f <file>`: Force delete modified file.
- `git rm --cached <file>`: Untrack file but keep locally.
- `git rm -r <folder>`: Recursively delete and stage folder.

## Undo and Restore

- `git restore <file>`: Restore file to last commit.
- `git restore .`: Restore all files.
- `git restore --staged <file>`: Unstage file.
- `git reset --hard`: Discard all changes and deletions.

## Stash

- `git stash`: Temporarily save uncommitted changes.
- `git stash pop`: Restore and remove latest stash.
- `git stash apply`: Restore latest stash (keeps in list).
- `git stash list`: List stashes.
- `git stash drop`: Remove specific stash.

## Advanced

- `git diff <commit1> <commit2>`: Compare commits.
- `git revert <commit-ID>`: Create new commit reversing specific commit.
- `git rebase <branch>`: Rebase current branch onto another for linear history (local only).

