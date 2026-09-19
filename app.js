(() => {
  const data = window.__RISK_DATA__;
  const history = window.__RISK_HISTORY__ || [];
  if (!data) return;

  const color = score => score <= 0 ? "var(--s0)" : score === 1 ? "var(--s1)" : score === 2 ? "var(--s2)" : "var(--s3)";
  const scoreColor = value => value < 25 ? "var(--s0)" : value < 45 ? "var(--s1)" : value < 65 ? "var(--s2)" : "var(--s3)";
  const riskWord = score => ["NORMAL","WATCH","HIGH","SEVERE"][Math.max(0, Math.min(3, score))];
  const esc = v => String(v ?? "—").replace(/[&<>"']/g, s => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]));

  document.getElementById("score").textContent = Math.round(data.score);
  document.getElementById("level").textContent = data.level;
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("updated").textContent = "Updated " + new Date(data.updated_at).toLocaleString("ja-JP", {timeZone:"Asia/Tokyo"});

  const ring = document.getElementById("scoreRing");
  ring.style.setProperty("--p", Math.min(100, Math.max(0, data.score)));
  ring.style.setProperty("--accent", scoreColor(data.score));
  document.getElementById("level").style.color = scoreColor(data.score);

  const tx = data.transmission || {stage:0,label:"CALM",note:"—"};
  document.getElementById("stageNum").textContent = tx.stage;
  document.getElementById("stageLabel").textContent = tx.label;
  document.getElementById("stageNote").textContent = tx.note;

  const flags = document.getElementById("flags");
  (data.flags || []).forEach(f => {
    const el = document.createElement("span");
    el.className = "flag " + (f.type === "CLEAR" ? "" : "hot");
    el.textContent = f.label;
    flags.appendChild(el);
  });

  const pillars = document.getElementById("pillars");
  (data.pillars || []).forEach(p => {
    const el = document.createElement("article");
    el.className = "pillar";
    el.style.setProperty("--accent", scoreColor(p.score));
    el.innerHTML = '<div class="pillar-top"><span>'+esc(p.name)+'</span><b>'+Math.round(p.score)+'</b></div><div class="track"><div class="fill" style="width:'+Math.max(0,Math.min(100,p.score))+'%"></div></div>';
    pillars.appendChild(el);
  });

  const ladderDef = [
    ["0","CALM","広範な伝播なし"],
    ["1","SECTOR REPRICING","AI / Private Credit内のストレス"],
    ["2","CREDIT TRANSMISSION","社債市場へ伝播"],
    ["3","FUNDING STRESS","流動性・資金調達へ伝播"],
    ["4","SYSTEMIC / FREEZE","信用・資金市場が同時に深刻化"]
  ];
  const ladder = document.getElementById("ladder");
  ladderDef.forEach((s,i) => {
    const el = document.createElement("article");
    el.className = "step " + (i === tx.stage ? "active" : i < tx.stage ? "passed" : "");
    el.style.setProperty("--accent", i < 1 ? "var(--s0)" : i < 2 ? "var(--s1)" : i < 3 ? "var(--s2)" : "var(--s3)");
    el.innerHTML = '<b>STAGE '+s[0]+'</b><h3>'+s[1]+'</h3><p>'+s[2]+'</p>';
    ladder.appendChild(el);
  });

  const grid = document.getElementById("grid");
  [...(data.indicators || [])].sort((a,b) => b.score - a.score || b.weight - a.weight).forEach(item => {
    const el = document.createElement("article");
    el.className = "card";
    el.style.setProperty("--accent", color(item.score));
    const bars = [1,2,3].map(n => '<i class="'+(item.score >= n ? "on" : "")+'"></i>').join("");
    const source = item.source_url
      ? '<a href="'+esc(item.source_url)+'" target="_blank" rel="noreferrer">'+esc(item.source)+' ↗</a>'
      : esc(item.source);
    el.innerHTML =
      '<div class="card-top"><div><h3>'+esc(item.name)+'</h3><span class="riskword">'+riskWord(item.score)+'</span></div><span class="mode">'+esc(item.mode)+'</span></div>'+
      '<div class="value">'+esc(item.value)+'</div>'+
      '<div class="meta"><span>'+source+'</span><span>as of '+esc(item.as_of || "—")+'</span></div>'+
      '<p class="note">'+esc(item.note)+'</p>'+
      '<div class="riskline"><div class="bars">'+bars+'</div><span class="riskword">'+item.score+'/3</span><span class="weight">WEIGHT '+esc(item.weight)+'%</span></div>';
    grid.appendChild(el);
  });

  const d = data.diagnostics || {};
  const diagItems = [
    ["US 10Y", d.us10y == null ? "—" : d.us10y.toFixed(2)+"%"],
    ["US 2Y", d.us2y == null ? "—" : d.us2y.toFixed(2)+"%"],
    ["2s10s", d.curve_2s10s_bps == null ? "—" : d.curve_2s10s_bps.toFixed(0)+" bp"],
    ["VIX", d.vix == null ? "—" : d.vix.toFixed(2)],
    ["10Y RV20", d.realized_10y_vol_bps == null ? "pending" : d.realized_10y_vol_bps.toFixed(0)+" bp ann."],
    ["MOVE", d.move_manual == null ? "manual未入力" : Number(d.move_manual).toFixed(1)],
    ["Italy–Bund", d.italy_bund_bps == null ? "—" : d.italy_bund_bps.toFixed(0)+" bp"],
    ["WTI", d.wti == null ? "—" : "$"+d.wti.toFixed(2)]
  ];
  const diag = document.getElementById("diagnostics");
  diagItems.forEach(x => {
    const el=document.createElement("div"); el.className="diag";
    el.innerHTML='<span>'+esc(x[0])+'</span><strong>'+esc(x[1])+'</strong>';
    diag.appendChild(el);
  });

  renderHistory(history);

  function renderHistory(rows){
    const box = document.getElementById("historyChart");
    if (!rows.length){
      box.innerHTML='<div style="padding:55px 18px;color:var(--muted);font-size:12px">履歴は次回自動更新から蓄積されます。</div>';
      return;
    }
    const last=rows[rows.length-1];
    document.getElementById("historyLast").textContent = last.date+"  "+Math.round(last.score)+"/100";
    const w=1000,h=180,pad=16;
    const xs=rows.map((_,i)=>rows.length===1?w/2:pad+i*(w-2*pad)/(rows.length-1));
    const ys=rows.map(r=>h-pad-(Math.max(0,Math.min(100,r.score))/100)*(h-2*pad));
    let path="";
    xs.forEach((x,i)=>{path+=(i?" L ":"M ")+x.toFixed(1)+" "+ys[i].toFixed(1)});
    const circles=xs.map((x,i)=>'<circle cx="'+x+'" cy="'+ys[i]+'" r="'+(i===xs.length-1?6:3)+'" fill="'+scoreColor(rows[i].score)+'"/>').join("");
    const area=rows.length>1 ? path+' L '+xs[xs.length-1]+' '+(h-pad)+' L '+xs[0]+' '+(h-pad)+' Z' : "";
    box.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-label="stress history">'+
      (area?'<path d="'+area+'" fill="rgba(114,167,255,.08)"/>':'')+
      '<path d="'+path+'" fill="none" stroke="#72a7ff" stroke-width="4" vector-effect="non-scaling-stroke"/>'+circles+
      '</svg>';
  }
})();
