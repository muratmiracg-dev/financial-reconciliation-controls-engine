"use strict";
const $ = (id) => document.getElementById(id);
let result = null;
const fmt = (v, c) =>
  v === null
    ? "—"
    : new Intl.NumberFormat("en-US", { style: "currency", currency: c }).format(
        v / 100,
      );
function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}
function download(name, text, type = "text/plain") {
  const a = document.createElement("a"),
    url = URL.createObjectURL(new Blob([text], { type }));
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function demo() {
  const response = await fetch("/api/demo");
  if (!response.ok) throw Error("Demo unavailable");
  return response.json();
}
async function run(data) {
  $("message").textContent = "Checking inputs and reconciling…";
  $("run").disabled = $("demo").disabled = true;
  result = null;
  ["csv", "json"].forEach((id) => ($(id).disabled = true));
  $("rows").replaceChildren();
  $("issues").replaceChildren();
  $("balances").replaceChildren();
  $("detail").hidden = true;
  ["matched", "review", "issueCount", "bankCount"].forEach(
    (id) => ($(id).textContent = "—"),
  );
  try {
    const r = await fetch("/api/reconcile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...data,
        days: Number($("days").value),
        tolerance: Number($("tolerance").value),
      }),
    });
    const body = await r.json();
    if (!r.ok) throw Error(body.error);
    result = body;
    render();
    $("message").textContent =
      "Reconciliation complete. Review exceptions before taking any action.";
  } catch (e) {
    $("message").textContent = "Unable to reconcile: " + e.message;
    $("runid").textContent = "Run failed";
  } finally {
    $("run").disabled = $("demo").disabled = false;
  }
}
function render() {
  ["matched", "review"].forEach((k) => ($(k).textContent = result.summary[k]));
  $("issueCount").textContent = result.issues.length;
  $("bankCount").textContent = result.counts.bank;
  $("runid").textContent = "Run " + result.run_id;
  ["csv", "json"].forEach((id) => ($(id).disabled = false));
  $("balances").replaceChildren();
  for (const [c, v] of Object.entries(result.totals)) {
    $("balances").append(
      node(
        "div",
        `${c} · Matched gross ${fmt(v.matched_gross, c)} / Unresolved gross ${fmt(v.unresolved_gross, c)}`,
      ),
    );
  }
  renderRows();
  $("issues").replaceChildren();
  for (const x of result.issues) {
    const el = node("div", undefined, "exception");
    el.append(
      node("b", x.code),
      node("p", x.detail),
      node("small", x.source + " / " + x.ids.join(", ")),
    );
    $("issues").append(el);
  }
  if (!result.issues.length)
    $("issues").append(node("p", "No control exceptions."));
}
function renderRows() {
  if (!result) return;
  $("rows").replaceChildren();
  const q = $("search").value.toLowerCase();
  let count = 0;
  for (const g of result.groups) {
    if ($("status").value && g.status !== $("status").value) continue;
    if (!JSON.stringify(g).toLowerCase().includes(q)) continue;
    count++;
    const tr = node("tr");
    const first = node("td", g.id);
    first.append(node("small", g.party));
    tr.append(
      first,
      node("td", g.shape),
      node("td", fmt(g.bank_amount, g.currency)),
      node("td", fmt(g.difference, g.currency)),
      node(
        "td",
        g.rule === "REFERENCE" ? "Reference · 100" : `Heuristic · ${g.score}`,
      ),
    );
    const status = node("td");
    status.append(
      node(
        "span",
        g.status,
        "badge " + (g.status === "REVIEW" ? "review" : ""),
      ),
    );
    tr.append(status);
    tr.tabIndex = 0;
    tr.setAttribute("aria-label", "Inspect " + g.id);
    const inspect = () => {
      const d = $("detail");
      d.hidden = false;
      d.replaceChildren(
        node("b", g.id + " · " + g.party),
        node(
          "p",
          "Bank: " +
            g.bank_ids.join(", ") +
            " | Invoices: " +
            g.invoice_ids.join(", "),
        ),
        node(
          "p",
          "Rule: " + g.rule + " · Evidence strength: " + g.score + "/100",
        ),
        node(
          "p",
          g.flags.length
            ? "Review reasons: " + g.flags.join(" · ")
            : "Invoice amount, bank movement and balanced ledger evidence agree within policy.",
        ),
      );
    };
    tr.onclick = inspect;
    tr.onkeydown = (e) => {
      if (e.key === "Enter") inspect();
    };
    $("rows").append(tr);
  }
  if (!count) {
    const tr = node("tr"),
      td = node("td", "No settlements match this filter.", "empty");
    td.colSpan = 6;
    tr.append(td);
    $("rows").append(tr);
  }
}
$("demo").onclick = async () => {
  try {
    await run(await demo());
  } catch (e) {
    $("message").textContent = e.message;
  }
};
$("run").onclick = async () => {
  try {
    const data = {};
    for (const k of ["bank", "invoices", "journal"]) {
      const file = $(k).files[0];
      if (!file) throw Error("Select all three CSV files.");
      if (file.size > 2 * 1024 * 1024)
        throw Error("Maximum file size is 2 MB.");
      data[k] = await file.text();
    }
    await run(data);
  } catch (e) {
    $("message").textContent = e.message;
  }
};
$("search").oninput = renderRows;
$("status").onchange = renderRows;
$("json").onclick = () =>
  download(
    "reconciliation-" + result.run_id + ".json",
    JSON.stringify(result, null, 2),
    "application/json",
  );
$("csv").onclick = () => {
  const cols = [
    "id",
    "status",
    "party",
    "currency",
    "bank_amount",
    "invoice_amount",
    "difference",
    "rule",
    "score",
    "shape",
    "bank_ids",
    "invoice_ids",
    "flags",
  ];
  const escape = (v) => {
    let s = Array.isArray(v) ? v.join(";") : v === null ? "" : String(v);
    if (typeof v === "string" && /^[\s]*[=+@-]/.test(s)) s = "'" + s;
    return '"' + s.replaceAll('"', '""') + '"';
  };
  download(
    "settlements-minor-units.csv",
    [
      cols.join(","),
      ...result.groups.map((g) => cols.map((k) => escape(g[k])).join(",")),
    ].join("\r\n"),
    "text/csv",
  );
};
document.querySelectorAll(".sample").forEach(
  (button) =>
    (button.onclick = async () => {
      try {
        download(
          button.dataset.kind + ".csv",
          (await demo())[button.dataset.kind],
          "text/csv",
        );
      } catch (e) {
        $("message").textContent = e.message;
      }
    }),
);
