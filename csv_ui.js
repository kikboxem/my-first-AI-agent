/* Accessible no-upload UI: uploaded CSV bytes never leave this browser tab. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const api = window.ValuePilotAudit;
  if (!api) return;
  let latest = null;
  const currency = (num, code) => code + " " + num.toLocaleString("en-US", {maximumFractionDigits: 0});
  const status = $("csv-status");
  const input = $("csv-file");
  const tableBody = $("csv-rows");
  const top = $("csv-summary");
  const exportButton = $("csv-export");
  const note = $("csv-notice");
  const currentDate = () => {
    const d = new Date();
    return [d.getFullYear(),String(d.getMonth()+1).padStart(2,"0"),String(d.getDate()).padStart(2,"0")].join("-");
  };
  function setStatus(message, error = false) {
    status.textContent = message;
    status.classList.toggle("csv-error",error);
  }
  function addCell(row, value, className) {
    const td=document.createElement("td");
    td.textContent = String(value);
    if(className) td.className=className;
    row.appendChild(td);
  }
  function metric(label,value){
    const wrapper=document.createElement("div");
    wrapper.className="csv-metric";
    const k=document.createElement("small"),v=document.createElement("strong");
    k.textContent=label;v.textContent=String(value);
    wrapper.append(k,v);
    return wrapper;
  }
  function display(result, label) {
    latest=result;
    exportButton.disabled=false;
    top.replaceChildren(
      metric("Open opportunities",result.stats.active),
      metric("Flagged for review",result.stats.flagged),
      metric("Overdue",result.stats.overdue),
      metric("Weighted pipeline",currency(result.stats.expectedRevenue,result.currency))
    );
    tableBody.replaceChildren();
    for(const r of result.records.slice(0,100)){
      const tr=document.createElement("tr");
      addCell(tr,r.priority_rank||"—");
      addCell(tr,r.company);
      addCell(tr,currency(r._expected,r.currency),"numeric-cell");
      addCell(tr,r.risk_flags);
      addCell(tr,r.suggested_next_action);
      tableBody.appendChild(tr);
    }
    const hidden = Math.max(0, result.records.length-100);
    note.textContent=(hidden ? "Showing first 100 ranked opportunities; all rows are included in the export. " : "")
      +"Priority score is a review heuristic, not proven recoverable revenue. Nothing has been sent or contacted.";
    setStatus(label+": "+result.stats.totalRows+" records analyzed locally. "
      + result.stats.flagged+" need review; "+result.stats.stale+" have no contact in 14+ days.");
  }
  function process(text,label){
    try{ display(api.audit(text,currentDate()),label); }
    catch(e){
      latest=null;exportButton.disabled=true;top.replaceChildren();tableBody.replaceChildren();
      note.textContent="No data retained after a validation failure.";
      setStatus(e.message||"Unable to read CSV",true);
    }
  }
  // Custom label is also keyboard-operable when the native input is visually hidden.
  const pickerLabel = document.querySelector('label[for="csv-file"]');
  if (pickerLabel) pickerLabel.addEventListener("keydown", event => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });
  input.addEventListener("change", async()=>{
    const file=input.files && input.files[0];
    if(!file)return;
    if(file.size>1024*1024){setStatus("File exceeds the 1 MB safety limit.",true);return;}
    try{process(await file.text(),file.name);}
    catch{setStatus("Could not read the selected file.",true);}
    finally{input.value="";}
  });
  $("csv-sample").addEventListener("click",()=>process(api.syntheticSample(new Date()),"Synthetic sample"));
  $("csv-clear").addEventListener("click",()=>{
    latest=null;
    input.value="";
    top.replaceChildren();tableBody.replaceChildren();
    exportButton.disabled=true;
    note.textContent="No CSV data is stored on the server or in browser storage.";
    setStatus("Cleared. Choose a CSV or load the synthetic sample.");
  });
  exportButton.addEventListener("click",()=>{
    if(!latest)return;
    const content=api.exportCSV(latest.records);
    const blob=new Blob([content],{type:"text/csv;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const link=document.createElement("a");
    link.href=url;link.download="valuepilot-reviewed-opportunities.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    setStatus("Downloaded reviewable report with "+latest.records.length+" opportunities. No outreach was performed.");
  });
  $("csv-template").addEventListener("click",()=>{
    const blob=new Blob([api.syntheticSample(new Date())],{type:"text/csv;charset=utf-8"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download="valuepilot-synthetic-sample.csv";
    document.body.appendChild(a);a.click();a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    setStatus("Downloaded synthetic example CSV.");
  });
  setStatus("Choose a CSV, or use the synthetic example to explore the workflow. All analysis stays on your device.");
})();