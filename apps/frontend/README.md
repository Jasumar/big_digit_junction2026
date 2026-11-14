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

## Language

**Answer charts follow the answer's language** (en/fi/sv): the backend gets the language
from the AI, and `apps/bank-backend/present.py` translates labels, category, basket and
spender-type names (from `packages/cloud/glossary.py`) and formats money, percentages
and dates (Finnish: `1 904 €`, `23 %`, `30.9.2026`). The answer JSON has `lang`.

**UI language switch** (T012): FI / SV / EN in the header; Finnish by default; the choice
is saved in the browser (`localStorage` key `coach.lang`). `i18n.js` holds every fixed text
(placeholder, suggestion chips, home card, messages) and formats money, percentages and
dates per language; basket names on the home card come from the backend glossary
(`/api/overview?lang=`). The selected language is sent with each question as a fallback
for the AI. Add a UI text: add the key to all three languages in `i18n.js` —
`apps/frontend/i18n.test.mjs` (run by `scripts/test.sh`) fails if one is missing.

## Conventions

`index.html` shell, `app.js` renders the home card and answers, `styles.css`. An answer
is `{text, insights, visuals, trace}`; visuals are `stats`, `bars`, `table` — to add a
visual type, add it in `bank-backend/present.py` and in `renderVisual`.

## Follow-up questions

`renderAnswer` shows `answer.follow_ups` as buttons under the answer ("clarify" ones in
orange). Tapping sends the button's `prompt` as the next question (with the current UI
language) and disables the row. Labels come from the backend in the answer's language.
