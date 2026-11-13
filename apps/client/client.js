// Client layer: the only code the UI uses to reach the S-pankki backend (step 1 and 7).
// Plain ES module, no dependencies. Shapes: packages/contracts/.

export class CoachError extends Error {}

export function createClient({ baseUrl = "", timeoutMs = 30000 } = {}) {
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
    customers: (limit = 12) => request("/api/customers?limit=" + limit).then((b) => b.customers),
    overview: (customerId) => request("/api/overview?customer_id=" + encodeURIComponent(customerId)),
    // Command -> Answer. `history` is optional: [{role: "user"|"coach", text}]
    command: (customerId, text, history = []) =>
      request("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, text, history: history.slice(-6) }),
      }),
  };
}
