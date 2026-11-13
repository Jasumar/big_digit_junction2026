# Tasks

One file per unit of work. A task file is the contract between the person doing the
work, the people working next to them, and any agent involved.

## Lifecycle

```bash
# 1. create from the template, next free number
cp docs/tasks/TEMPLATE.md docs/tasks/T007-upload-endpoint.md
$EDITOR docs/tasks/T007-upload-endpoint.md      # fill in every section

# 2. branch + worktree, same slug
git worktree add .worktrees/task-t007-upload-endpoint \
                -b task/t007-upload-endpoint main

# 3. work, commit with the task id in the message
#    git commit -m "T007: add upload endpoint"

# 4. merge into main, then clean up
git worktree remove .worktrees/task-t007-upload-endpoint
git branch -d task/t007-upload-endpoint
```

Commit the task file itself on `main` (or in the branch — either is fine, as long as
the `Status:` line matches reality). Update `Status:` when you start, block, and merge.

## Rules

- **One owner per task.** Not two people, not "whoever gets there first".
- **Allowed files are a hard boundary.** If the list is wrong, fix the list before
  coding, and mention it in the channel.
- **Small enough to merge the same day.** If not, split it — a task that spans the
  contract *and* two apps is three tasks.
- **Dependencies must be merged first.** Check the `Dependencies` section before you
  start; starting early on an unmerged dependency is how rework happens.
- **Templates are not decisions.** Anything marked `TODO` stays undecided until the
  team decides it in `docs/MASTER_PLAN.md`.

## Index

Keep `docs/MASTER_PLAN.md` §Task ownership as the table of active tasks; it is what
people scan when deciding what to pick up next.
