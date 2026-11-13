# Contributing

Mandatory rules for everyone working in this repository — humans and AI agents.
Optimised for: many people and agents working in parallel for a short time, merging
often, breaking each other as little as possible.

If something here blocks you, fix the rule in a PR or raise it in the team channel.
Silently deviating is the one thing that is not allowed.

---

## TL;DR

```bash
# 1. get your task
#    docs/tasks/T005-upload-endpoint.md   (create from docs/tasks/TEMPLATE.md)

# 2. one branch + one worktree per task
git worktree add .worktrees/task-t005-upload-endpoint -b task/t005-upload-endpoint main

# 3. work inside your allowed files, commit often
cd .worktrees/task-t005-upload-endpoint
git add -A && git commit -m "T005: add upload endpoint"

# 4. sync with main, resolve, verify, then merge
git fetch origin && git rebase origin/main
bash scripts/check.sh
cd ../.. && git checkout main && git merge --no-ff task/t005-upload-endpoint

# 5. clean up
git worktree remove .worktrees/task-t005-upload-endpoint
git branch -d task/t005-upload-endpoint
```

---

## 1. One task = one file = one branch = one worktree

Every non-trivial change starts as a task file in `docs/tasks/`:

- Filename: `T<nnn>-<slug>.md` (e.g. `T005-upload-endpoint.md`), next free number.
- Created from `docs/tasks/TEMPLATE.md`. Fill in owner, allowed files, dependencies,
  acceptance criteria **before** writing code.
- Branch: `task/t<nnn>-<slug>` — the same slug as the file.
- Worktree: `.worktrees/task-t<nnn>-<slug>` — same name, gitignored.

Why worktrees: separate directories, one Git repository. Two branches can be checked
out at once, so you never stash, never lose uncommitted work when switching, and two
agents cannot trip over each other's index. They share the same `.git`, so commits,
branches and merges are the same as usual.

Allowed branch prefixes: `task/`, `fix/`, `docs/`, `spike/`, `infra/`.
`main` is protected: no direct pushes, no force-pushes.

### Worktree commands

```bash
git worktree add .worktrees/task-t005-upload-endpoint -b task/t005-upload-endpoint main
git worktree list                          # see all active worktrees
cd .worktrees/task-t005-upload-endpoint

# leaving a branch checked out in a worktree is why `git checkout` fails elsewhere;
# remove the worktree first, then the branch
git worktree remove .worktrees/task-t005-upload-endpoint
git branch -d task/t005-upload-endpoint
git worktree prune                          # clean up stale metadata after a manual rm -rf
```

Note: `git worktree add` refuses an existing branch — that is the normal error after
`git checkout -b` was already run for that name. Use `git worktree add <path>
<existing-branch>` instead of `-b`.

---

## 2. Stay inside your allowed files

Each task file lists **Allowed files** and, where relevant, **Read-only / off-limits**
paths. This is the merge-conflict budget: two tasks must not edit the same file
unless the task files say so.

Files that many tasks want to touch — `README.md`, `docs/MASTER_PLAN.md`,
`docs/SYSTEM_MAP.md`, `AGENTS.md`, root config — are **shared**. Before editing one:

1. Say so in your task file (`Shared files touched: …`).
2. Make the smallest possible edit; do not reformat the rest of the file.
3. Rebase onto `main` immediately before merging, not an hour earlier.

If you need a file you do not own, add it to your task file and get agreement in the
team channel first.

---

## 3. Contracts are the source of truth

`packages/contracts/` defines the API shape (requests, responses, errors). The
frontend and backend both depend on it; neither may define its own competing version.

Rules:

- Change the contract **first**, in a dedicated commit, with the reason in the commit
  message and in the task file.
- Update every consumer in the same PR. A contract change that leaves a consumer
  broken is not mergeable.
- Contract changes are announced in the team channel before merging — anyone else
  mid-flight may be building against the old shape.
- Never hand-copy types across the frontend/backend boundary. Import from the
  contract package.

`TODO`: the concrete mechanism (generated client, shared type definitions, OpenAPI
spec) is decided with the stack. When it is, document it here and in
`packages/contracts/README.md`.

---

## 4. Database changes

`packages/db/` owns schema and migrations.

- One migration per change. Never edit a migration that has been merged to `main` —
  add a new one.
- Announce schema changes in your task file and in the team channel; another task may
  be reading or writing the same tables.
- Migrations and seed data must be runnable from a clean checkout with one documented
  command (`TODO`: fill in once the stack is chosen).
- Destructive changes (dropping columns, rewriting data) need a second pair of eyes
  even at hackathon speed.

---

## 5. Merge small, merge often

- Target: a branch lives **hours, not days**. If a task is bigger than that, split it
  into two task files.
- Rebase onto `main` before merging — `git fetch origin && git rebase origin/main`.
  Merge commits are allowed (`--no-ff`) for landing; rebase for syncing.
- Resolve conflicts in your own branch, never by reverting someone else's work.
- If a conflict means someone else's change and yours cannot both be right, stop and
  talk to them. Do not guess.
- Delete the branch and worktree after merging.

Merge checklist (the PR template mirrors this):

- [ ] Task file exists and is filled in; acceptance criteria met.
- [ ] Only allowed files touched (plus declared shared files).
- [ ] `bash scripts/check.sh` passes.
- [ ] Lint / type check / test / build pass — as far as they exist (see `README.md`).
- [ ] Contract change? Consumers updated + team told.
- [ ] DB change? Migration added, clean-run command documented.
- [ ] No `.env`, `preferences.md`, secrets, build output, or `node_modules` committed.

---

## 6. Checks and CI

- `bash scripts/check.sh` runs the repo hygiene checks locally; CI runs the same
  script, so local green means CI green for those checks.
- Stack-specific checks (lint, type check, test, build) are wired into the same CI
  workflow as they appear. Anything a PR promises must be runnable with one command
  from the repo root.
- A red `main` is everyone's problem. Fix it before starting new work; if you cannot,
  say so in the channel immediately.

---

## 7. Secrets and local config

- Never commit `.env`, API keys, tokens, or personal paths.
- `.env.example` is tracked and lists keys with **empty** values. Adding a variable =
  adding a line to `.env.example` in the same commit.
- `preferences.md` (agent workflow preferences) is gitignored on purpose — each person
  runs their own agent setup. Only `preferences.example.md` is tracked.
- If a secret is committed by accident: rotate the key first, then clean history. Do
  not assume deleting the line is enough.

---

## 8. Commits

- One line, prefixed with the task id: `T005: add upload endpoint`.
- Body explains *why* when it is not obvious; list unplanned fixes there too.
- Do not mix unrelated changes in one commit. Do not commit generated files.

---

## 9. Working with AI agents

- Agents must read `AGENTS.md` first; that file binds them to these rules.
- Give an agent **one task file** and nothing else. "Improve the frontend" produces
  conflicts and unowned decisions.
- An agent may not add a dependency, pick a framework, create a package, or change a
  contract without the task file saying so.
- Review agent diffs like anyone else's: scope, allowed files, "verified" claims that
  were never actually run.
