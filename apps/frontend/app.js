import { createClient } from "/client/client.js";
import { DEFAULT_LANG, LANGS, makeT } from "./i18n.js";

const api = createClient();
const $ = (id) => document.getElementById(id);
const LANG_KEY = "coach.lang";
let t = makeT(LANGS.includes(localStorage.getItem(LANG_KEY)) ? localStorage.getItem(LANG_KEY) : DEFAULT_LANG);
const TONE = { essentials: "var(--essentials)", necessities: "var(--necessities)",
  everyday: "var(--everyday)", peer: "var(--peer)", good: "var(--good)", warn: "var(--warn)" };
let customerId = null;
let history = [];
let customers = [];
let lastOverview = null;
let sampleCount = null;

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.textContent = html;
  return e;
}

// ---------------------------------------------------------------- home
function renderHome(o) {
  const home = $("home");
  home.replaceChildren();
  const s = o.safe_to_spend, b = o.breakdown;
  home.append(el("h2", "", t("customerHeading", { id: o.customer.customer_id, age: o.customer.age })));
  if (s && s.as_of) home.append(el("div", "asof", t("dataUntil", { date: t.date(s.as_of) })));
  const hero = el("div", "hero");
  if (s) hero.append(stat(t("safeWeek"), t.eur(s.safe_to_spend),
    { comfortable: "good", tight: "warn", very_tight: "bad" }[s.status],
    t("balance", { amount: t.eur(s.balance) })));
  if (b) hero.append(stat(t("spent30"), t.eur(b.total_spend), "",
    b.change_pct == null ? "" : t("vsBefore", { pct: t.pct(b.change_pct, true) })));
  home.append(hero);
  if (b && b.total_spend > 0) {
    const bar = el("div", "stack");
    const legend = el("div", "legend");
    for (const k of b.buckets) {
      const seg = el("div");
      seg.style.cssText = "width:" + k.share_pct + "%;background:" + TONE[k.bucket];
      const label = (o.bucket_labels && o.bucket_labels[k.bucket]) || k.label;
      seg.title = label;
      bar.append(seg);
      const l = el("span");
      l.innerHTML = '<i class="dot" style="background:' + TONE[k.bucket] + '"></i>';
      l.append(label + " " + t.eur(k.amount));
      legend.append(l);
    }
    home.append(bar, legend);
  }
}

function stat(label, value, tone, sub) {
  const d = el("div", "stat " + (tone === "good" ? "good" : tone || ""));
  d.append(el("div", "l", label), el("div", "v", value));
  if (sub) d.append(el("div", "s", sub));
  return d;
}

// ---------------------------------------------------------------- visuals
function renderVisual(v) {
  if (v.type === "stats") {
    const d = el("div", "hero");
    for (const i of v.items) d.append(stat(i.label, i.value, i.tone, i.sub));
    return d;
  }
  if (v.type === "bars") {
    const d = el("div", "bars");
    if (v.title) d.append(el("h3", "", v.title));
    const max = Math.max(1, ...v.items.map((i) => i.value));
    for (const i of v.items) {
      const row = el("div", "bar");
      const track = el("div", "track");
      const fill = el("div", "fill");
      fill.style.width = (100 * i.value) / max + "%";
      fill.style.background = TONE[i.tone] || "var(--muted)";
      track.append(fill);
      const val = el("div", "val", i.display);
      if (i.note) val.append(Object.assign(el("small", "", i.note)));
      row.append(el("div", "lbl", i.label), track, val);
      d.append(row);
    }
    return d;
  }
  if (v.type === "table") {
    const d = el("div", "tbl");
    if (v.title) d.append(el("h3", "", v.title));
    const t = el("table");
    if (v.columns && v.columns.some(Boolean)) {
      const tr = el("tr");
      for (const c of v.columns) tr.append(el("th", "", c));
      t.append(tr);
    }
    for (const r of v.rows) {
      const tr = el("tr");
      for (const c of r) tr.append(el("td", "", c));
      t.append(tr);
    }
    d.append(t);
    return d;
  }
  return el("div");
}

function renderAnswer(a) {
  const box = el("div", "msg coach");
  // a.notice (what the tools could not cover) is not shown as a box: the answer text
  // already says it, because the backend passes it to the model (team decision, #61)
  box.append(el("p", "", a.text));
  for (const v of a.visuals) box.append(renderVisual(v));
  for (const i of a.insights) {
    const d = el("div", "insight " + (i.kind || "info"));
    d.append(el("b", "", i.title));
    if (i.body) d.append(document.createTextNode(i.body));
    box.append(d);
  }
  if (a.follow_ups && a.follow_ups.length) {  // tappable next questions (idea: CuriousGeorg1)
    const row = el("div", "followups");
    for (const f of a.follow_ups) {
      const b = el("button", "chip" + (f.kind === "clarify" ? " clarify" : ""), f.label);
      b.type = "button";
      b.title = f.prompt;
      b.onclick = () => { for (const x of row.querySelectorAll("button")) x.disabled = true; ask(f.prompt); };
      row.append(b);
    }
    box.append(row);
  }
  const blocked = a.trace.filter((t) => !t.approved);
  if (blocked.length) box.append(el("div", "trace", t("notAllowed") + blocked.map((x) => x.note).join("; ")));
  return box;
}

// ---------------------------------------------------------------- chat
async function ask(text) {
  text = text.trim();
  if (!text || !customerId) return;
  const chat = $("chat");
  const me = el("div", "msg me");
  me.append(el("span", "", text));
  const wait = el("div", "msg typing", t("thinking"));
  chat.append(me, wait);
  wait.scrollIntoView({ behavior: "smooth", block: "end" });
  $("q").value = "";
  setBusy(true);
  try {
    const a = await api.command(customerId, text, history, t.lang);
    history.push({ role: "user", text }, { role: "coach", text: a.text });
    wait.replaceWith(renderAnswer(a));
  } catch (e) {
    wait.replaceWith(el("div", "msg coach err", e.message));
  } finally {
    setBusy(false);
    chat.lastElementChild.scrollIntoView({ behavior: "smooth", block: "end" });
  }
}

function setBusy(b) {
  $("ask").querySelector("button").disabled = b;
}

async function loadCustomer(id) {
  customerId = id;
  history = [];
  $("chat").replaceChildren();
  $("home").replaceChildren(el("div", "skeleton", t("loading")));
  await refreshHome();
}

async function refreshHome() {
  try {
    lastOverview = await api.overview(customerId, t.lang);
    renderHome(lastOverview);
  } catch (e) {
    $("home").replaceChildren(el("div", "err", e.message));
  }
}

// ---------------------------------------------------------------- language
function applyLanguage() {
  document.documentElement.lang = t.lang;
  document.title = "S-Bank " + t("title");
  $("title").textContent = t("title");
  $("customer-label").textContent = t("customerLabel");
  $("customer").setAttribute("aria-label", t("customerLabel"));
  $("langs").setAttribute("aria-label", t("langLabel"));
  $("q").placeholder = t("placeholder");
  $("q").setAttribute("aria-label", t("questionLabel"));
  $("send").setAttribute("aria-label", t("send"));
  for (const b of $("langs").querySelectorAll("button")) {
    b.setAttribute("aria-pressed", String(b.dataset.lang === t.lang));
  }
  const chips = $("chips");
  chips.replaceChildren();
  for (const s of t.list("suggestions")) {
    const b = el("button", "chip", s);
    b.type = "button";
    b.onclick = () => ask(s);
    chips.append(b);
  }
  const sel = $("customer");
  for (const opt of sel.options) {
    const c = customers.find((x) => x.customer_id === opt.value);
    if (c) opt.textContent = t("customerOption", { id: c.customer_id, age: c.age });
  }
  if (sampleCount != null) $("banner").textContent = t("sample", { n: sampleCount });
}

async function setLanguage(lang) {
  if (!LANGS.includes(lang) || lang === t.lang) return;
  t = makeT(lang);
  localStorage.setItem(LANG_KEY, lang);
  applyLanguage();
  if (customerId) await refreshHome();  // basket names come from the backend glossary
}

async function init() {
  for (const b of $("langs").querySelectorAll("button")) b.onclick = () => setLanguage(b.dataset.lang);
  applyLanguage();
  $("ask").onsubmit = (e) => { e.preventDefault(); ask($("q").value); };
  try {
    const h = await api.health();
    if (h.data && h.data.source === "fixture") {
      sampleCount = h.data.customers;
      $("banner").textContent = t("sample", { n: sampleCount });
      $("banner").hidden = false;
    }
  } catch (_) {}
  try {
    customers = await api.customers(12);
    const sel = $("customer");
    for (const c of customers) sel.append(new Option(t("customerOption", { id: c.customer_id, age: c.age }), c.customer_id));
    sel.onchange = () => loadCustomer(sel.value);
    await loadCustomer(customers[0].customer_id);
  } catch (e) {
    $("home").replaceChildren(el("div", "err", e.message));
  }
}

init();
