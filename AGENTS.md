# AGENTS.md

Rules for AI coding agents working in this repository. Read this before your first
action in a session. Humans: these are the same rules as `docs/CONTRIBUTING.md`,
written for an agent.

If `preferences.md` exists in the repository root, read it too. It holds the local
operator's personal workflow preferences. **Shared project rules in this file and in
`docs/` always take priority over `preferences.md`** — if they conflict, follow the
project rules and say so in your report.

## 1. Read before you work

Read, in this order, and only as deep as your task needs:

1. `docs/tasks/<your-task>.md` — the task you were given, if one exists.
2. `docs/MASTER_PLAN.md` — scope, milestones, ownership.
3. `docs/SYSTEM_MAP.md` — module boundaries and what depends on what.
4. The `README.md` of the app or package you are touching.
5. `docs/CONTRIBUTING.md` — workflow, branches, merge rules.
6. `preferences.md` — if present.

Do not start editing on the basis of a summary, a previous session's memory, or an
assumption about the stack: the stack is not chosen yet. If a document contradicts
your plan, the document wins; report the contradiction instead of silently
following one side.

## 2. Respect ownership and module boundaries

- Every directory has an owner (`docs/SYSTEM_MAP.md` §Module ownership) and a
  dependency direction. Do not import across a boundary the map forbids.
- Work inside your task's **allowed files**. If you need a file outside that list,
  stop and ask; do not widen your own scope.
- Do not create new top-level directories, packages, or apps. Do not add
  dependencies, frameworks, or tooling — the stack is undecided and adding one
  pre-empts a decision that belongs to the team.
- Do not implement product features that no task file asks for.

## 3. Coordinate shared contract and database changes

- `packages/contracts/` is the single source of truth for the API shape. Changing it
  affects every consumer: update the contract **and** the consumers in the same
  change, and note the change in your task file.
- `packages/db/` schema and migrations are shared state. One migration per change,
  never edit an already-merged migration, and announce schema changes in the task
  file before writing them.
- If your change requires a contract or schema change you were not asked to make,
  stop and report it instead of making it.

## 4. Verify before you claim done

- Run the checks that exist: `bash scripts/check.sh`, plus the lint / type check /
  test / build commands from `README.md` §Commands once the stack defines them.
- Run the commands your task file lists under "Acceptance criteria".
- Never report success on the basis of a written file or a passing single command if
  the task asked for behaviour. Report what actually ran and what it returned.
- If a check cannot run (no stack yet, missing tool, missing env var), say so
  explicitly — never fabricate output, and never fill a `TODO` command with a
  plausible-looking one.

## 5. Leave the repo in a mergeable state

- Commit small, on your task branch, with a message naming the task id.
- Do not merge into `main` yourself unless the task says you own the merge.
- Do not commit `.env`, `preferences.md`, generated artifacts, or dependency
  directories. `.gitignore` covers the usual cases; check `git status` before
  committing.
- Do not rewrite history on shared branches, force-push, or delete other people's
  branches.

## Reporting

State, in your final message: what changed (files), what you verified (commands and
their real output), what you did **not** verify, and any decision you had to make
without confirmation. Keep it short — the diff is the detail.
