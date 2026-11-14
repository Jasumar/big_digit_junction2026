// Fixed UI text in Finnish, Swedish and English. The AI's answers and charts are localized
// by the backend; this file covers everything else the user sees. Finnish/Swedish wording
// is a draft to be checked by native speakers (docs/MASTER_PLAN.md question 11).

export const LANGS = ["fi", "sv", "en"];
export const DEFAULT_LANG = "fi";

export const STRINGS = {
  fi: {
    title: "Rahavalmentaja",
    customerLabel: "Esimerkkiasiakas",
    customerOption: "{id} ({age} v)",
    loading: "Ladataan tietojasi…",
    customerHeading: "Asiakas {id} · {age} v",
    dataUntil: "Tiedot {date} asti — \"tässä kuussa\" ja \"tänään\" viittaavat tähän päivään",
    safeWeek: "Turvallisesti käytettävissä tällä viikolla",
    balance: "Saldo {amount}",
    spent30: "Kulutus, viimeiset 30 päivää",
    vsBefore: "{pct} edelliseen",
    placeholder: "Kysy rahoistasi mitä tahansa…",
    questionLabel: "Kysymyksesi",
    send: "Lähetä",
    thinking: "Mietin…",
    notAllowed: "Ei sallittu: ",
    sample: "Vain esimerkkidata ({n} asiakasta). Lataa koko aineisto ennen demoa.",
    langLabel: "Kieli",
    suggestions: [
      "Mihin rahani menivät tässä kuussa?",
      "Millainen kuluttaja olen?",
      "Paljonko voin turvallisesti kuluttaa tällä viikolla?",
      "Miten voisin säästää enemmän?",
      "Mitä jos vähentäisin ulkona syömistä 20 %?",
      "Miten vertaudun muihin ikäisiini?",
      "Näytä ravintolakuluni kuukausittain",
    ],
  },
  sv: {
    title: "Pengacoach",
    customerLabel: "Exempelkund",
    customerOption: "{id} ({age} år)",
    loading: "Laddar dina uppgifter…",
    customerHeading: "Kund {id} · {age} år",
    dataUntil: "Data till {date} — \"den här månaden\" och \"i dag\" syftar på det datumet",
    safeWeek: "Tryggt att spendera den här veckan",
    balance: "Saldo {amount}",
    spent30: "Utgifter, senaste 30 dagarna",
    vsBefore: "{pct} jämfört med innan",
    placeholder: "Fråga vad som helst om dina pengar…",
    questionLabel: "Din fråga",
    send: "Skicka",
    thinking: "Tänker…",
    notAllowed: "Inte tillåtet: ",
    sample: "Endast exempeldata ({n} kunder). Ladda hela datamängden före demon.",
    langLabel: "Språk",
    suggestions: [
      "Vart tog mina pengar vägen den här månaden?",
      "Vilken typ av konsument är jag?",
      "Hur mycket kan jag tryggt spendera den här veckan?",
      "Hur kan jag spara mer?",
      "Vad händer om jag äter ute 20 % mindre?",
      "Hur står jag mig jämfört med andra i min ålder?",
      "Visa mina restaurangutgifter per månad",
    ],
  },
  en: {
    title: "Money Coach",
    customerLabel: "Demo customer",
    customerOption: "{id} ({age})",
    loading: "Loading your money…",
    customerHeading: "Customer {id} · age {age}",
    dataUntil: "Data until {date} — \"this month\" and \"today\" refer to that date",
    safeWeek: "Safe to spend this week",
    balance: "Balance {amount}",
    spent30: "Spent, last 30 days",
    vsBefore: "{pct} vs before",
    placeholder: "Ask your money anything…",
    questionLabel: "Your question",
    send: "Send",
    thinking: "Thinking…",
    notAllowed: "Not allowed: ",
    sample: "Sample data only ({n} customers). Load the full dataset before the demo.",
    langLabel: "Language",
    suggestions: [
      "Where did my money go this month?",
      "What kind of spender am I?",
      "What can I safely spend this week?",
      "How could I save more?",
      "What if I cut dining out by 20%?",
      "How do I compare to others my age?",
      "Show my restaurant spending by month",
    ],
  },
};

const NBSP = " ";

export function makeT(lang) {
  const s = STRINGS[lang] || STRINGS[DEFAULT_LANG];
  const t = (key, vars = {}) =>
    String(s[key] ?? STRINGS.en[key] ?? key).replace(/\{(\w+)\}/g, (_, k) => vars[k] ?? "");
  t.lang = STRINGS[lang] ? lang : DEFAULT_LANG;
  t.list = (key) => s[key] || STRINGS.en[key] || [];
  // money: en "€1,879"; fi/sv "1 879 €"
  t.eur = (x) => {
    const n = Math.round(Math.abs(x)).toLocaleString("en-US");
    const sign = x < 0 ? "-" : "";
    return t.lang === "en" ? sign + "€" + n : sign + n.replace(/,/g, NBSP) + NBSP + "€";
  };
  t.pct = (x, signed = false) => {
    const n = Math.round(x);
    const s2 = (signed && n > 0 ? "+" : "") + n;
    return t.lang === "en" ? s2 + "%" : s2 + NBSP + "%";
  };
  t.date = (iso) => {
    const [y, m, d] = String(iso).split("-");
    if (!d) return iso;
    if (t.lang === "en") {
      const mon = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ")[Number(m) - 1];
      return Number(d) + " " + mon + " " + y;
    }
    return Number(d) + "." + Number(m) + "." + y;
  };
  return t;
}
