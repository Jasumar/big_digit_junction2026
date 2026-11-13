# apps/bank-backend/calculation

**Calculation tools** in the architecture (`docs/SYSTEM_MAP.md`). A module inside the
S-pankki backend, not a separate service. **Not scaffolded.**

Owner: same as `apps/bank-backend/` unless `docs/SYSTEM_MAP.md` says otherwise.

- Flow steps: receives **3** (an already-approved calculation request), does **4**
  (calculates over client data in `packages/cloud/`), returns **5** (results or a
  response explaining why not).
- Owns: the set of calculations (each a named tool with typed input and output), and
  the only code path that reads client financial data.
- Not its job: deciding whether a request is allowed (the backend does that before
  calling in), talking to the AI model, or formatting answers for the user.

The AI model never sees raw client data, only what these tools return. Keep it that
way unless `docs/MASTER_PLAN.md` §Decision log says otherwise.

## Tools

`TODO`: list each tool — name, inputs, output, what data it reads. The shapes go in
`packages/contracts/`.
