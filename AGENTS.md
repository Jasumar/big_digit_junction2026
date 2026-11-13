# AGENTS.md

Rules for AI agents in this repo. Read this before acting. `preferences.md` (root,
gitignored) may add personal preferences; these rules and `docs/` outrank it.

## 1. Read first

Your task file if you have one, then `docs/MASTER_PLAN.md`, `docs/SYSTEM_MAP.md`, and
the README of the directory you are touching. Nothing here describes a chosen stack —
if a document contradicts your plan, the document wins; say so instead of choosing.

## 2. Stay in bounds

Work only in the files your task allows. Do not add dependencies, frameworks, packages
or top-level directories, and do not build features no task asks for.

## 3. Shared surfaces: ask, do not change

A shared surface is anything more than one part of the system depends on: the API
contract, the shape of stored data, shared config keys, root tooling, `docs/`.

- If your task does not explicitly grant authority over it, **do not change it**.
  Report the conflict, what depends on it, and the smallest change that would unblock
  you. A conflict raised is a good outcome; a silent change is not.
- With authority, change it once, update every consumer in the same change, and say so
  in your report.
- Never duplicate a shared surface locally to avoid touching it.

## 4. Verify

Run what exists: `bash scripts/check.sh` plus whatever your task lists. Report what
actually ran and what it returned. If something cannot run, say that — never invent
output, never fill a `TODO` with a plausible command.

## 5. Leave it mergeable

Commit small on your task branch with the task id in the message. Do not merge, rewrite
shared history, or delete other branches unless your task says you own that. No `.env`,
secrets, dependencies or build output.

## Report

What changed, what you ran and got, what you did not verify, what you decided alone.
Short — the diff is the detail.
