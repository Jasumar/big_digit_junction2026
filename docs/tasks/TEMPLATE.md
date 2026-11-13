# Task template

Copy this file to `docs/tasks/T<nnn>-<slug>.md`, fill every section, then create the
branch and worktree from the same slug. Delete the guidance lines in angle brackets.

Keep tasks small enough to merge the same day. If it does not fit, split it.

---

# T<nnn> — <short imperative title>

**Owner:** <name / handle; exactly one>
**Status:** todo | in progress | blocked | review | merged
**Branch:** `task/t<nnn>-<slug>`
**Worktree:** `.worktrees/task-t<nnn>-<slug>`
**Area:** frontend | backend | contracts | db | infra | docs

## Goal

<1–3 sentences: what exists after this task that does not exist before. Describe the
outcome, not the steps.>

## Context — read first

- <docs/tasks/T<nnn>-<dep>.md (dependency)>
- <docs/MASTER_PLAN.md §…>
- <docs/SYSTEM_MAP.md §…>
- <apps/<app>/README.md>

## Allowed files

The only paths this task may modify. Anything else needs agreement first.

```text
apps/<app>/...
```

**Read-only / off-limits:**

```text
packages/contracts/**   # unless this task is the contract change
docs/MASTER_PLAN.md
```

**Shared files touched:** <list, or "none">

## Dependencies

- **Needs merged first:** <T<nnn>, or "none">
- **Blocks:** <T<nnn>, or "none">
- **Contract impact:** <none | describe the shape change and who consumes it>
- **Schema impact:** <none | tables/columns, plus the migration name>

## Acceptance criteria

Checkable statements. Each must be verifiable by a command, a test, or a named manual
step. "Works well" is not an acceptance criterion.

- [ ] <behaviour the demo depends on>
- [ ] <error/empty case handled>
- [ ] <contract consumer updated, if contract change>
- [ ] <documentation updated: app README / SYSTEM_MAP, if boundary changed>

## Verification

Commands that must pass before merging (fill in once the stack exists; leave `TODO`
rather than inventing one):

```bash
bash scripts/check.sh
# TODO: lint / type check / test for this area
```

Manual check:

1. <step>
2. <expected result>

## Notes / decisions

<Anything you had to decide that the task did not specify, and anything you
deliberately did not do. Reviewers read this section first.>
