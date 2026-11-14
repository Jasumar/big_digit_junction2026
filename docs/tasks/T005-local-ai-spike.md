# T005 — Local AI model spike

**Owner:** `TODO` **Status:** review (built in MVP, see Decisions.md)
**Branch:** `spike/t005-local-ai`

## Goal

Answer open question 4: a model and runtime that runs on hardware we have, answers in
acceptable time, and can ask for a calculation in a structured way (tool call or JSON).
Leave a runnable setup in `apps/ai/`.

## Allowed files

```text
apps/ai/**
```

**Shared surfaces touched:** none. Findings go to the owner of `docs/MASTER_PLAN.md`
for the Decision log.

## Depends on

- Needs merged first: T001
- Blocks: T007

## Acceptance criteria

- [ ] `apps/ai/README.md` Setup: how to get and start the model locally, hardware used.
- [ ] Measured: time to answer one realistic question on the demo machine.
- [ ] The model produces a well-formed calculation request for one sample question.
- [ ] Recommendation and fallback written in the task Notes.

## Verify

```bash
bash scripts/check.sh
# TODO: the command that runs the sample question
```

## Notes

Time-box it. A weaker model that answers in seconds beats a strong one that takes a
minute on stage.
