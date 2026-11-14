# T012 — UI language switch (Finnish, Swedish, English)

**Owner:** `TODO` **Status:** review
**Branch:** `task/t012-ui-language`

## Goal

The user picks Finnish, Swedish or English in the header; all fixed UI text — the input
prompt, suggestion chips, home card and messages — follows the choice. Finnish is the
default and the choice is remembered. The AI keeps answering in the question's language
and uses the selection only as a fallback.

## Allowed files

```text
apps/frontend/**          (i18n.js, i18n.test.mjs, app.js, index.html, styles.css, README)
apps/client/client.js     (lang on command and overview)
apps/bank-backend/orchestrator.py, server.py, tests/test_flow.py
apps/ai/llm_provider.py   (fallback language in the rules)
packages/contracts/schemas.py
scripts/test.sh           (run the UI text check)
docs/
```

**Shared surfaces touched:** COMMAND gains optional `lang`; `/api/overview` accepts
`lang` and returns `bucket_labels`; `scripts/test.sh` also runs a Node check — all
additive, consumers updated in the same change.

## Depends on

- Needs merged first: T010 (merged in PR #6)

## Acceptance criteria

- [x] FI / SV / EN switch in the header; Finnish by default; choice saved in the browser.
- [x] Placeholder, 7 suggestion chips, home card, basket names, data-date line,
      "thinking", error/sample messages and labels follow the choice.
- [x] Money, percent and dates on the home card formatted per language.
- [x] Basket names on the home card come from the backend glossary (one source).
- [x] AI: answers in the question's language; selection used when unclear and as the
      default for charts/notices when a provider does not report a language.
- [x] Tests: 52 Python tests + UI text check (all keys in all languages, formats).
- [x] Checked in the browser: default Finnish, switch to SV/EN, reload keeps the choice,
      a Finnish chip gets a Finnish answer and Finnish charts.

## Verify

```bash
bash scripts/check.sh
bash scripts/test.sh
python3 apps/bank-backend/server.py   # then use the FI/SV/EN switch at http://localhost:8000
```

## Notes

Swedish and Finnish UI wording are drafts for a native speaker (MASTER_PLAN Q11). The
customer dropdown hides the app title on screens narrower than 400 px so the controls
fit. Decisions #51–53.
