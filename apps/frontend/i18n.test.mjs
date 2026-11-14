// UI text checks. Run: node apps/frontend/i18n.test.mjs (also run by scripts/test.sh)
import assert from "node:assert/strict";
import { DEFAULT_LANG, LANGS, STRINGS, makeT } from "./i18n.js";

const keys = Object.keys(STRINGS.en);
for (const lang of LANGS) {
  for (const k of keys) assert.ok(k in STRINGS[lang], `${lang} is missing "${k}"`);
  assert.equal(STRINGS[lang].suggestions.length, STRINGS.en.suggestions.length,
    `${lang} should have as many suggestion chips as English`);
}
assert.equal(DEFAULT_LANG, "fi");

const NB = " ";
const fi = makeT("fi"), sv = makeT("sv"), en = makeT("en");
assert.equal(fi.eur(3797.4), `3${NB}797${NB}€`);
assert.equal(en.eur(3797.4), "€3,797");
assert.equal(en.eur(-12), "-€12");
assert.equal(fi.pct(-25.4, true), `-25${NB}%`);
assert.equal(en.pct(8, true), "+8%");
assert.equal(fi.date("2026-09-30"), "30.9.2026");
assert.equal(sv.date("2026-09-30"), "30.9.2026");
assert.equal(en.date("2026-09-30"), "30 Sep 2026");
assert.equal(fi("customerHeading", { id: "CUST1", age: 63 }), "Asiakas CUST1 · 63 v");
assert.equal(makeT("xx").lang, "fi");  // unknown language falls back to the default
assert.equal(sv.list("suggestions")[0], "Vart tog mina pengar vägen den här månaden?");
console.log("i18n: ok (" + LANGS.length + " languages, " + keys.length + " keys)");
