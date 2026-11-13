# Contributing

Rules for everyone, humans and agents. Short on purpose.

## One task, one branch, one worktree

```bash
cp docs/tasks/TEMPLATE.md docs/tasks/T007-upload-endpoint.md   # fill it in first
git worktree add .worktrees/task-t007-upload-endpoint -b task/t007-upload-endpoint main
cd .worktrees/task-t007-upload-endpoint
git commit -m "T007: add upload endpoint"

# before merging: rebase, check, merge
git rebase main            # or: git fetch origin && git rebase origin/main
bash scripts/check.sh
cd ../.. && git checkout main && git merge --no-ff task/t007-upload-endpoint

# after merging
git worktree remove .worktrees/task-t007-upload-endpoint
git branch -d task/t007-upload-endpoint
```

Worktrees share one `.git`, so two branches can be checked out at once — no stashing,
no lost work, agents cannot step on each other's index. `git worktree list` shows them;
`git worktree prune` clears stale ones.

Branch prefixes: `task/`, `fix/`, `docs/`, `spike/`, `infra/`. `main` is protected.

## Shared surfaces

A shared surface is anything more than one part of the system depends on. Typically:

- the API contract in `packages/contracts/`
- the shape of stored data, and anything that reads or writes it
- shared config keys and `.env.example`
- root tooling: `scripts/`, `.github/`, `AGENTS.md`, `README.md`, `docs/`
- files another task lists as its allowed files

Rules:

- **Do not change one silently.** If you need a change, raise it: what breaks, what
  you need, smallest option. The owner decides or grants it.
- **Authority comes from your task file**, or a clear yes from whoever owns it. A task
  that says "may change `packages/contracts/`" has authority; a task that is silent
  does not.
- With authority: change it once, update every consumer in the same change, note it in
  the task file and tell the team — someone mid-flight may depend on the old shape.
- Never copy a shared definition into your own module to avoid the conversation.

## Allowed files

Each task lists the paths it may modify. That list is the merge-conflict budget. Shared
doc/root files need a line in the task file (`Shared files touched:`), a minimal edit,
and a rebase right before merging.

## Merge small, merge often

Hours, not days. If a task is bigger, split it. Rebase to sync, `--no-ff` to land.
Resolve conflicts in your branch; never revert someone else's work. If a conflict means
two changes cannot both be right, stop and talk.

Checklist (mirrored in the PR template):

- [ ] Task file filled in; acceptance criteria met.
- [ ] Only allowed files touched.
- [ ] Shared surfaces changed only with authority, consumers updated.
- [ ] `bash scripts/check.sh` passes, plus any lint/test/build the area has.
- [ ] No secrets, `.env`, dependencies or build output committed.

## Checks and secrets

`scripts/check.sh` runs locally and in CI; keep it fast and dependency-free. Add real
checks to CI as they appear, with one command to run them from the repo root.

Never commit `.env`, keys or tokens; `.env.example` lists keys with empty values.
`preferences.md` is gitignored because it is personal. A committed secret means
rotating the key first, not deleting the line.

## Commits

`T007: add upload endpoint` — task id, one line, why in the body when it is not obvious.
No mixed unrelated changes, no generated files.

## Agents

Give an agent one task file. Review its diff like anyone else's: scope, allowed files,
and "verified" claims that never ran.
