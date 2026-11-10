// Reproducible, dependency-free CSV audit checks: node tests/test_csv_audit.cjs
const assert = require("node:assert/strict");
const audit = require("../csv_audit.js");
const today = "2026-11-10";
const header = audit.HEADERS.join(",");
const rows = [
  "L1,Acme Industries,10000,USD,proposal,2026-10-10,Maya,60,2026-11-01",
  "L2,Northwind,5000,USD,qualified,2026-11-09,Alex,20,2026-11-15",
  "L3,Closed Company,9000,USD,closed won,2026-10-09,Maya,100,2026-10-10",
  "L4,No Due Date,2000,USD,new,,Alex,25,"
];
const text = header + "\n" + rows.join("\n");
const result = audit.audit(text,today);
assert.equal(result.records.length,4);
assert.equal(result.stats.active,3);
assert.equal(result.stats.flagged,2);
assert.equal(result.stats.overdue,1);
assert.equal(result.stats.stale,1);
assert.equal(result.stats.expectedRevenue,7500);
assert.equal(result.stats.flaggedExpectedRevenue,6500);
assert.equal(result.records[0].lead_id,"L1");
assert.match(result.records[0].risk_flags,/Overdue/);
assert.ok(result.records.find(x=>x.lead_id==="L3")._closed);
assert.match(audit.exportCSV(result.records),/priority_rank/);
assert.match(audit.exportCSV(result.records),/suggested_next_action/);
assert.equal(audit.parseCSV('a,b\n"One, Two","a""b"\n')[1][1],'a"b');
assert.equal(audit.parseCSV('\uFEFFa,b\r\n1,2\r\n').length,2);
assert.throws(()=>audit.parseCSV('a\n"unterminated'),/Unclosed/);
assert.throws(()=>audit.audit(header+"\n"+rows[0]+"\n"+rows[0],today),/Duplicate/);
assert.throws(()=>audit.audit(header+"\n"+rows[0].replace("USD","EUR")+"\n"+rows[1],today),/Mixed currencies/);
assert.throws(()=>audit.audit(header+"\n"+rows[0].replace("2026-11-01","2026-02-30"),today),/calendar date/);
assert.throws(()=>audit.audit(header+"\n"+rows[0].replace(",60,",",-1,"),today),/win_probability/);
assert.throws(()=>audit.audit("lead_id,company\n1,Test",today),/Missing required/);
assert.equal(audit.safeExportCell("  =HYPERLINK(1)"),"'  =HYPERLINK(1)".replace(/^/,'"').replace(/$/,'"'));
assert.equal(audit.safeExportCell("-2"),'"\'-2"');
const injection = "L9,=2+3,2000,USD,proposal,2026-11-01,Alex,20,2026-11-02";
const csv = audit.exportCSV(audit.audit(header+"\n"+injection,today).records);
assert.ok(csv.includes('"\'=2+3"'),"Formula injection must be neutralized for spreadsheet export");
const sample = audit.audit(audit.syntheticSample(new Date("2026-11-10T12:00:00Z")),today);
assert.equal(sample.records.length,8);
assert.equal(sample.stats.active,7);
console.log("PASS 20+ offline CSV parsing, validation, scoring and safe export checks");
