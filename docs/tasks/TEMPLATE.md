# Task template

Copy to `docs/tasks/T<nnn>-<slug>.md`, fill it in, create the branch from the same slug.
Keep it small enough to merge the same day; if not, split it.

---

# T<nnn> — <short imperative title>

**Owner:** <one name> **Status:** todo | in progress | blocked | review | merged
**Branch:** `task/t<nnn>-<slug>`

## Goal

<What exists after this that did not before. Outcome, not steps.>

## Allowed files

Everything else needs agreement first.

```text
apps/<app>/...
```

**Shared surfaces touched:** <none, or which, and who agreed>

## Depends on

- Needs merged first: <T<nnn> | none>
- Blocks: <T<nnn> | none>

## Acceptance criteria

Each one checkable by a command, a test, or a named manual step.

- [ ] <behaviour the demo needs>
- [ ] <error / empty case>
- [ ] <consumers updated, if a shared surface changed>

## Verify

```bash
bash scripts/check.sh
# TODO: anything else this area has — leave TODO rather than inventing a command
```

## Notes

<What you decided alone, and what you deliberately did not do.>
