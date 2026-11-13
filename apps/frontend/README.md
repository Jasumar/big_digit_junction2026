# apps/frontend

**UI / Frontend** in the architecture (`docs/SYSTEM_MAP.md`). What the user sees and
does: ask a question, see the answer, insights and charts. Plain HTML/CSS/JS,
no build; served by the backend.

Owner: `TODO` (`docs/SYSTEM_MAP.md`)

- Talks to: `apps/client/` only (two-way). Never calls the S-pankki backend, the AI
  model or the cloud directly.
- Depends on: `packages/contracts/` (UI ↔ client shapes).
- Owns: screens, styling, UI state, rendering answers and insights.
- Not its job: auth, session handling, server logic, or its own copy of shared shapes.

## Setup

`python3 apps/bank-backend/server.py`, open http://localhost:8000 (phone-width layout).
No install. No automated UI tests; the API it uses is covered by the backend tests.

## Conventions

`index.html` shell, `app.js` renders the home card and answers, `styles.css`. An answer
is `{text, insights, visuals, trace}`; visuals are `stats`, `bars`, `table` — to add a
visual type, add it in `bank-backend/present.py` and in `renderVisual`.
