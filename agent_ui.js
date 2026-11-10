
(() => {
  const presets={
    roi:{title:"Automation ROI",desc:"Estimate the financial potential of automating a repeatable workflow, including operating costs and assumptions.",prompt:"Our 12 employees each save 3 hours per week from automation. Loaded hourly cost is 35 USD, 50% of the saved time creates value, software costs 300 USD/month, setup costs 2000 USD. Calculate first-year ROI.",sample:"Example: 12 employees, 3 hours saved weekly, $35/h cost.",note:"Modeled staff capacity is not guaranteed cash savings"},
    sales:{title:"Sales pipeline uplift",desc:"Model incremental revenue and gross profit from a hypothetical improvement in your team's conversion rate.",prompt:"We have 200 qualified leads per month, current win rate 10%, target win rate 12%, average deal value 3000 USD, gross margin 35%. Estimate incremental monthly revenue and gross profit.",sample:"Example: 200 leads, conversion increases from 10% to 12%.",note:"Conversion improvements are hypothetical"},
    lead:{title:"Lead prioritization",desc:"Estimate the probability-weighted gross profit per selling hour for an opportunity.",prompt:"Prioritize a lead worth 20000 USD with 35% gross margin, 60% win probability, and 10 expected sales hours. Calculate expected gross profit per selling hour.",sample:"Example: $20,000 lead, 60% win chance, 10 selling hours.",note:"Win probability is a subjective input"},
    time:{title:"Global time",desc:"Ask for the time in another country. The tool returns AM/PM and a full local time-zone name.",prompt:"What time is it in Tokyo?",sample:"Example: What time is it in Tokyo?",note:"Time-zone abbreviations are expanded where available"}
  };
  const nav=[...document.querySelectorAll('.nav-tool')];
  const prompt=document.getElementById('prompt');
  const count=document.getElementById('counter');
  const answer=document.getElementById('answer');
  const run=document.getElementById('run');
  const state=document.getElementById('state');
  const copy=document.getElementById('copy');
  const sample=document.getElementById('example');
  let mode="roi";
  function setMode(next){
    mode=next;
    nav.forEach(x=>x.setAttribute('aria-selected',String(x.dataset.mode===next)));
    document.getElementById('csv-pane').hidden=next!=="csv";
    document.getElementById('agent-pane').hidden=next==="csv";
    if(next==="csv") return;
    const p=presets[next];
    document.getElementById('workflow-title').textContent=p.title;
    document.getElementById('workflow-description').textContent=p.desc;
    document.getElementById('assumption-note').textContent=p.note;
    prompt.value=p.prompt;
    count.textContent=prompt.value.length+" / 300";
    sample.textContent=p.sample+" ↗";
    answer.textContent="Run the agent to see the result of the selected Python tool.";
    answer.classList.add('placeholder');
    state.textContent="Ready";
    copy.disabled=true;
  }
  nav.forEach(button=>button.addEventListener('click',()=>setMode(button.dataset.mode)));
  sample.addEventListener('click',()=>{prompt.value=presets[mode].prompt;count.textContent=prompt.value.length+" / 300";prompt.focus()});
  prompt.addEventListener('input',()=>count.textContent=prompt.value.length+" / 300");
  document.getElementById('ask-form').addEventListener('submit',async e=>{
    e.preventDefault();
    if(run.disabled||!prompt.value.trim())return;
    run.disabled=true;run.textContent="Working…";state.textContent="Executing";copy.disabled=true;
    answer.textContent="Selecting and executing the relevant Python tool…";answer.classList.add('placeholder');
    const aborter=new AbortController();
    const timeout=setTimeout(()=>aborter.abort(),45000);
    try{
      const r=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:prompt.value.trim()}),signal:aborter.signal});
      const data=await r.json();
      if(!r.ok)throw new Error(data.error||"The request could not be completed.");
      answer.textContent=data.answer||"No result was returned.";
      answer.classList.remove('placeholder');state.textContent="Completed";copy.disabled=false;
    }catch(err){
      answer.textContent=err.name==="AbortError"?"The request timed out. Try again.":String(err.message||"Request failed.");
      state.textContent="Unavailable";
    }finally{clearTimeout(timeout);run.disabled=false;run.textContent="Run agent ↗"}
  });
  copy.addEventListener('click',async()=>{
    try{await navigator.clipboard.writeText(answer.textContent);copy.textContent="Copied";setTimeout(()=>copy.textContent="Copy result",1600)}
    catch{copy.textContent="Copy unavailable"}
  });
  setMode("csv");
})();
