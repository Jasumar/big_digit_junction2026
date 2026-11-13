import { createClient } from "/client/client.js";

const api = createClient();
const $ = (id) => document.getElementById(id);
const eur = (x) => "€" + Math.round(x).toLocaleString("en-FI");
const TONE = { essentials: "var(--essentials)", necessities: "var(--necessities)",
  everyday: "var(--everyday)", peer: "var(--peer)", good: "var(--good)", warn: "var(--warn)" };
const SUGGESTIONS = ["Where did my money go this month?", "What kind of spender am I?",
  "What can I safely spend this week?", "How could I save more?", "What if I cut dining out by 20%?", "How do I compare to others?",
  "Show my restaurant spending by month"];

let customerId = null;
let history = [];

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
  home.append(el("h2", "", "Customer " + o.customer.customer_id + " · age " + o.customer.age));
  const hero = el("div", "hero");
  if (s) hero.append(stat("Safe to spend this week", eur(s.safe_to_spend),
    { comfortable: "good", tight: "warn", very_tight: "bad" }[s.status], "Balance " + eur(s.balance)));
  if (b) hero.append(stat("Spent, last 30 days", eur(b.total_spend), "",
    b.change_pct == null ? "" : (b.change_pct > 0 ? "+" : "") + Math.round(b.change_pct) + "% vs before"));
  home.append(hero);
  if (b && b.total_spend > 0) {
    const bar = el("div", "stack");
    const legend = el("div", "legend");
    for (const k of b.buckets) {
      const seg = el("div");
      seg.style.cssText = "width:" + k.share_pct + "%;background:" + TONE[k.bucket];
      seg.title = k.label;
      bar.append(seg);
      const l = el("span");
      l.innerHTML = '<i class="dot" style="background:' + TONE[k.bucket] + '"></i>';
      l.append(k.label + " " + eur(k.amount));
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
  box.append(el("p", "", a.text));
  for (const v of a.visuals) box.append(renderVisual(v));
  for (const i of a.insights) {
    const d = el("div", "insight " + (i.kind || "info"));
    d.append(el("b", "", i.title));
    if (i.body) d.append(document.createTextNode(i.body));
    box.append(d);
  }
  const blocked = a.trace.filter((t) => !t.approved);
  if (blocked.length) box.append(el("div", "trace", "Not allowed: " + blocked.map((t) => t.note).join("; ")));
  return box;
}

// ---------------------------------------------------------------- chat
async function ask(text) {
  text = text.trim();
  if (!text || !customerId) return;
  const chat = $("chat");
  const me = el("div", "msg me");
  me.append(el("span", "", text));
  const wait = el("div", "msg typing", "Thinking…");
  chat.append(me, wait);
  wait.scrollIntoView({ behavior: "smooth", block: "end" });
  $("q").value = "";
  setBusy(true);
  try {
    const a = await api.command(customerId, text, history);
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
  $("home").replaceChildren(el("div", "skeleton", "Loading your money…"));
  try {
    renderHome(await api.overview(id));
  } catch (e) {
    $("home").replaceChildren(el("div", "err", e.message));
  }
}

async function init() {
  for (const s of SUGGESTIONS) {
    const b = el("button", "chip", s);
    b.type = "button";
    b.onclick = () => ask(s);
    $("chips").append(b);
  }
  $("ask").onsubmit = (e) => { e.preventDefault(); ask($("q").value); };
  try {
    const customers = await api.customers(12);
    const sel = $("customer");
    for (const c of customers) sel.append(new Option(c.customer_id + " (" + c.age + ")", c.customer_id));
    sel.onchange = () => loadCustomer(sel.value);
    await loadCustomer(customers[0].customer_id);
  } catch (e) {
    $("home").replaceChildren(el("div", "err", e.message));
  }
}

init();
