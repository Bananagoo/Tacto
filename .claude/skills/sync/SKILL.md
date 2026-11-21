---
name: sync
description: Check, commit and rebase onto the team's latest main without stepping on other lanes. Use when the user runs /sync or says "commit this" or "pull the latest".
argument-hint: "[commit message]"
disable-model-invocation: true
allowed-tools: Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git commit *) Bash(git pull --rebase *) Bash(git stash *) Bash(make *)
---

## Current state

```!
git status --short || true
git log --oneline -5 2>/dev/null || true
```

## Steps

1. Look at what changed. If files outside this session's lane (see the table in `CLAUDE.md`) are modified, list them and ask before including them.
2. Check that no secret is staged: nothing from `.env`, no string that looks like an API key. If there is one, stop and say so.
3. Run `make check`. If it fails, fix what this session broke; if the failure is in another lane, report it and stop.
4. Stage only the files that belong to this change. Commit with the message "$ARGUMENTS", or write one: imperative subject under 60 characters; prefix `contract:` if the contract changed.
5. `git pull --rebase origin main`. On conflict: resolve only files in this lane; for anything else, stop and show the conflict.
6. Run `make check` again if the pull brought anything in.
7. Do not push. Tell the user the commit is ready and what `git push` will send.
