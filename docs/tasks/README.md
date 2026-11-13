# Tasks

One file per unit of work: the contract between the person doing it, everyone working
next to them, and any agent.

```bash
cp docs/tasks/TEMPLATE.md docs/tasks/T042-upload-endpoint.md   # fill in, then
git worktree add .worktrees/task-t042-upload-endpoint -b task/t042-upload-endpoint main
```

Rules:

- One owner. Not two, not "whoever gets there first".
- Allowed files are a hard boundary; fix the list before coding, not after.
- Dependencies merged before you start.
- Small enough to merge the same day, otherwise split.
- A `TODO` in a template is not a decision.

Keep the index in `docs/MASTER_PLAN.md` §Tasks current. Update `Status:` when you
start, block, and merge.
