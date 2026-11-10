/* ValuePilot opportunity audit: fully offline, deterministic, browser-only. No network calls. */
(function (root) {
  "use strict";
  const HEADERS = ["lead_id", "company", "deal_value", "currency", "stage", "last_contact_date", "owner", "win_probability_percent", "next_action_due_date"];
  const OUTPUT = [...HEADERS, "expected_revenue", "priority_score", "priority_rank", "risk_flags", "suggested_next_action"];
  const MAX_BYTES = 1024 * 1024;
  const MAX_ROWS = 2000;
  const MAX_CELL = 400;
  const CLOSED_STAGES = new Set(["closed won", "won", "closed lost", "lost", "disqualified"]);
  const DANGEROUS = /^[\s\u0000-\u001f]*[=+\-@\t\r]/u;

  function parseCSV(input) {
    if (typeof input !== "string") throw new Error("Input must be CSV text.");
    if (new TextEncoder().encode(input).length > MAX_BYTES) throw new Error("CSV is too large (maximum 1 MB).");
    const text = input.replace(/^\uFEFF/, "");
    let rows = [], row = [], field = "", quoted = false, afterQuote = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"') {
          if (text[i+1] === '"') { field += '"'; i++; }
          else { quoted = false; afterQuote = true; }
        } else { field += ch; }
      } else if (afterQuote) {
        if (ch === ",") { row.push(field); field = ""; afterQuote = false; }
        else if (ch === "\n" || ch === "\r") {
          row.push(field); rows.push(row); row = []; field = ""; afterQuote = false;
          if (ch === "\r" && text[i+1] === "\n") i++;
        } else if (ch !== " " && ch !== "\t") throw new Error("Unexpected character after a quoted field.");
      } else if (ch === '"' && field === "") { quoted = true; }
      else if (ch === '"') { throw new Error("Unexpected quote inside an unquoted field."); }
      else if (ch === ",") { row.push(field); field = ""; }
      else if (ch === "\n" || ch === "\r") {
        row.push(field); rows.push(row); row = []; field = "";
        if (ch === "\r" && text[i+1] === "\n") i++;
      } else { field += ch; }
      if (field.length > MAX_CELL) throw new Error("CSV contains a field longer than 400 characters.");
      if (rows.length > MAX_ROWS + 1) throw new Error("CSV exceeds 2,000 data rows.");
    }
    if (quoted) throw new Error("Unclosed quoted field in CSV.");
    if (afterQuote || field !== "" || row.length > 0) { row.push(field); rows.push(row); }
    return rows.filter(r => !(r.length === 1 && r[0].trim() === ""));
  }

  function isoDate(text, allowBlank = true) {
    const v = (text || "").trim();
    if (!v && allowBlank) return "";
    if (!/^\d{4}-\d{2}-\d{2}$/.test(v)) throw new Error("Dates must use YYYY-MM-DD.");
    const d = new Date(v + "T00:00:00Z");
    if (!Number.isFinite(d.getTime()) || d.toISOString().slice(0, 10) !== v) throw new Error("Invalid calendar date: " + v);
    return v;
  }
  function amount(value, name, max) {
    const trimmed = String(value).trim();
    if (!/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(trimmed)) throw new Error("Invalid " + name + ": use a nonnegative number.");
    const n = Number(trimmed);
    if (!Number.isFinite(n) || n > max) throw new Error(name + " is outside the supported range.");
    return n;
  }
  function safeExportCell(value) {
    const text = String(value ?? "");
    // Prevent spreadsheet formula execution. Applies even to whitespace-prefixed payloads.
    const safe = DANGEROUS.test(text) ? "'" + text : text;
    return '"' + safe.replace(/"/g, '""') + '"';
  }
  function exportCSV(records) {
    const lines = [OUTPUT.map(safeExportCell).join(",")];
    records.forEach(r => lines.push(OUTPUT.map(h => safeExportCell(r[h] ?? "")).join(",")));
    return "\uFEFF" + lines.join("\r\n") + "\r\n";
  }

  function audit(text, dateISO = new Date().toISOString().slice(0, 10)) {
    const rows = parseCSV(text);
    if (!rows.length) throw new Error("The CSV has no header.");
    const rawHeaders = rows.shift().map(x => x.trim().toLowerCase());
    if (rawHeaders.length > 30 || new Set(rawHeaders).size !== rawHeaders.length) throw new Error("Duplicate or excessive CSV columns.");
    const missing = HEADERS.filter(h => !rawHeaders.includes(h));
    if (missing.length) throw new Error("Missing required columns: " + missing.join(", "));
    if (rows.length === 0) throw new Error("CSV contains no opportunities.");
    if (rows.length > MAX_ROWS) throw new Error("CSV exceeds 2,000 rows.");
    const today = isoDate(dateISO, false);
    const base = Date.parse(today + "T00:00:00Z");
    const ids = new Set(), currencies = new Set(), records = [];
    rows.forEach((row, i) => {
      const line = i + 2;
      if (row.length !== rawHeaders.length) throw new Error("Row " + line + " has a different number of columns.");
      const rec = {};
      HEADERS.forEach(h => rec[h] = String(row[rawHeaders.indexOf(h)] || "").trim());
      if (!rec.lead_id || !rec.company || !rec.currency || !rec.stage) throw new Error("Row " + line + " is missing lead_id, company, currency or stage.");
      if (ids.has(rec.lead_id)) throw new Error("Duplicate lead_id: " + rec.lead_id);
      ids.add(rec.lead_id);
      if (!/^[A-Z]{3}$/.test(rec.currency.toUpperCase())) throw new Error("Row " + line + ": currency must be a 3-letter code.");
      rec.currency = rec.currency.toUpperCase();
      currencies.add(rec.currency);
      const value = amount(rec.deal_value, "deal_value", 1000000000);
      const probability = amount(rec.win_probability_percent, "win_probability_percent", 100);
      const last = isoDate(rec.last_contact_date);
      const due = isoDate(rec.next_action_due_date);
      const closed = CLOSED_STAGES.has(rec.stage.toLowerCase().replace(/[_-]/g," ").trim());
      const stale = !closed && !!last && Math.floor((base - Date.parse(last + "T00:00:00Z")) / 86400000) >= 14;
      const overdue = !closed && !!due && due < today;
      const missingDate = !closed && !due;
      const neverContacted = !closed && !last;
      const flags = [];
      if (overdue) flags.push("Overdue next action");
      if (stale) flags.push("No contact in 14+ days");
      if (missingDate) flags.push("No next action date");
      if (neverContacted) flags.push("No recorded contact");
      const expected = closed ? 0 : value * probability / 100;
      const score = expected * (1 + (overdue ? .30 : 0) + (stale ? .15 : 0) + (missingDate ? .10 : 0));
      const action = closed ? "No action: closed opportunity"
        : overdue ? "Review overdue task and prepare an approved follow-up"
        : neverContacted ? "Verify lead qualification and schedule first contact"
        : stale ? "Review recent activity and prepare an approved follow-up"
        : missingDate ? "Assign next action and due date for review"
        : "Continue scheduled follow-up";
      records.push({
        ...rec,
        deal_value: value.toFixed(2),
        win_probability_percent: probability.toFixed(1),
        expected_revenue: expected.toFixed(2),
        priority_score: score.toFixed(2),
        priority_rank: "",
        risk_flags: flags.join("; ") || "No flagged issue",
        suggested_next_action: action,
        _closed: closed, _overdue: overdue, _stale: stale, _risk: !closed && flags.length > 0,
        _expected: expected, _score: score
      });
    });
    if (currencies.size > 1) throw new Error("Mixed currencies detected. Separate files by currency; no FX conversion is performed.");
    records.sort((a,b) => b._score - a._score || a.lead_id.localeCompare(b.lead_id));
    records.forEach((r,i) => r.priority_rank = r._closed ? "" : String(i+1));
    const active = records.filter(r=>!r._closed);
    const total = active.reduce((sum,r)=>sum+r._expected,0);
    const atRisk = active.filter(r=>r._risk);
    return {
      records,
      currency: records[0].currency,
      stats: {
        totalRows: records.length,
        active: active.length,
        flagged: atRisk.length,
        overdue: active.filter(r=>r._overdue).length,
        stale: active.filter(r=>r._stale).length,
        expectedRevenue: total,
        flaggedExpectedRevenue: atRisk.reduce((sum,r)=>sum+r._expected,0)
      }
    };
  }
  function syntheticSample(date = new Date()) {
    const toISO = days => {
      const d = new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth(),date.getUTCDate()));
      d.setUTCDate(d.getUTCDate()+days);
      return d.toISOString().slice(0,10);
    };
    const data = [
      ["OP-001","Northstar Solar",180000,"INR","proposal",toISO(-24),"Alex",65,toISO(-5)],
      ["OP-002","Pioneer Logistics",450000,"INR","negotiation",toISO(-3),"Maya",45,toISO(2)],
      ["OP-003","Maple Retail",95000,"INR","qualified",toISO(-17),"Alex",30,""],
      ["OP-004","Harbor Foods",210000,"INR","proposal",toISO(-21),"Sam",55,toISO(-1)],
      ["OP-005","Summit Manufacturing",390000,"INR","negotiation",toISO(-4),"Maya",70,toISO(3)],
      ["OP-006","Bluebird Services",75000,"INR","new","","Sam",15,""],
      ["OP-007","Atlas Digital",125000,"INR","closed won",toISO(-6),"Alex",100,toISO(-6)],
      ["OP-008","Cedar Health Supplies",275000,"INR","qualified",toISO(-15),"Maya",40,toISO(-2)]
    ];
    return [HEADERS.map(safeExportCell).join(","), ...data.map(r=>r.map(safeExportCell).join(","))].join("\r\n")+"\r\n";
  }
  const API={audit,parseCSV,exportCSV,syntheticSample,HEADERS,OUTPUT,safeExportCell};
  if (root) root.ValuePilotAudit=API;
  if (typeof module !== "undefined" && module.exports) module.exports=API;
})(typeof window !== "undefined" ? window : null);
