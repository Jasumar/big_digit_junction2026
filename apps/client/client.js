// Client layer: the only code the UI uses to reach the S-pankki backend (step 1 and 7).
// Plain ES module, no dependencies. Shapes: packages/contracts/.

export class CoachError extends Error {}

export function createClient({ baseUrl = "", timeoutMs = 150000 } = {}) {
  async function request(path, options = {}) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    let res;
    try {
      res = await fetch(baseUrl + path, { ...options, signal: ctrl.signal });
    } catch (e) {
      throw new CoachError(
        e.name === "AbortError" ? "The coach took too long to answer." : "Can't reach the bank right now."
      );
    } finally {
      clearTimeout(timer);
    }
    let body = null;
    try {
      body = await res.json();
    } catch (_) {}
    if (!res.ok) throw new CoachError((body && body.error) || "Something went wrong (" + res.status + ").");
    return body;
  }

  return {
    health: () => request("/api/health"),
    customers: (limit = 12) => request("/api/customers?limit=" + limit).then((b) => b.customers),
    overview: (customerId, lang) => request("/api/overview?customer_id=" + encodeURIComponent(customerId)
      + (lang ? "&lang=" + encodeURIComponent(lang) : "")),
    // Command -> Answer. `history` is optional: [{role: "user"|"coach", text}]
    // lang = the UI language: the AI answers in the question's language and falls back to it
    command: (customerId, text, history = [], lang) =>
      request("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, text, history: history.slice(-6),
                               ...(lang ? { lang } : {}) }),
      }),
  };
}
