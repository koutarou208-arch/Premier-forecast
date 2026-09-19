(() => {
  const data = window.__RISK_DATA__;
  const history = window.__RISK_HISTORY__ || [];
  const backtest = window.__BACKTEST_DATA__ || null;
  const neural = window.__NN_DATA__ || null;
  if (!data) return;

  const isV3 = Number(data.version || 0) >= 3;
  const clamp = v => Math.max(0, Math.min(100, Number(v || 0)));
  const scoreColor = value => {
    if (value == null) return "var(--muted)";
    return value < 25 ? "var(--s0)" : value < 45 ? "var(--s1)" : value < 65 ? "var(--s2)" : "var(--s3)";
  };
  const riskWord = value => {
    if (value == null) return "NO DATA";
    if (value < 25) return "NORMAL";
    if (value < 45) return "WATCH";
    if (value < 65) return "ELEVATED";
    if (value < 80) return "HIGH";
    return "CRITICAL";
  };
  const esc = v => String(v == null ? "—" : v).replace(/[&<>"']/g, s => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[s]));
  const displayScore = v => v == null ? "—" : Math.round(v);
  const componentValue = v => v == null ? null : clamp(v);

  document.getElementById("score").textContent = displayScore(data.score);
  document.getElementById("level").textContent = data.level || "NO DATA";
  document.getElementById("summary").textContent = data.summary || "—";
  document.getElementById("updated").textContent = "Updated " + new Date(data.updated_at).toLocaleString("ja-JP", {timeZone:"Asia/Tokyo"});

  const ring = document.getElementById("scoreRing");
  ring.style.setProperty("--p", clamp(data.score));
  ring.style.setProperty("--accent", scoreColor(data.score));
  document.getElementById("level").style.color = scoreColor(data.score);

  const coverage = document.getElementById("coverage");
  const breadth = document.getElementById("breadth");
  const rawScore = document.getElementById("rawScore");
  const syncBonus = document.getElementById("syncBonus");
  if (coverage) coverage.textContent = data.coverage_pct == null ? (isV3 ? "—" : "V2") : Math.round(data.coverage_pct) + "%";
  if (breadth) breadth.textContent = data.breadth && data.breadth.score != null ? Math.round(data.breadth.score) + "%" : "—";
  if (rawScore) rawScore.textContent = data.raw_score == null ? displayScore(data.score) : Number(data.raw_score).toFixed(1);
  if (syncBonus) syncBonus.textContent = data.synchronization_bonus == null ? "+0.0" : "+" + Number(data.synchronization_bonus).toFixed(1);

  const tx = data.transmission || {stage:0,label:"CALM",note:"—"};
  document.getElementById("stageNum").textContent = tx.stage;
  document.getElementById("stageLabel").textContent = tx.label;
  document.getElementById("stageNote").textContent = tx.note;

  const flags = document.getElementById("flags");
  if (!isV3) {
    const legacy = document.createElement("span");
    legacy.className = "flag hot";
    legacy.textContent = "V3 engine installed — refresh pending";
    flags.appendChild(legacy);
  }
  (data.flags || []).forEach(f => {
    const el = document.createElement("span");
    el.className = "flag " + (f.type === "CLEAR" ? "" : "hot");
    el.textContent = f.label;
    flags.appendChild(el);
  });

  const pillars = document.getElementById("pillars");
  (data.pillars || []).forEach(p => {
    const value = p.score == null ? 0 : p.score;
    const el = document.createElement("article");
    el.className = "pillar";
    el.style.setProperty("--accent", scoreColor(p.score));
    el.innerHTML =
      '<div class="pillar-top"><span>'+esc(p.name)+'</span><b>'+displayScore(p.score)+'</b></div>'+
      '<div class="track"><div class="fill" style="width:'+clamp(value)+'%"></div></div>';
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
  [...(data.indicators || [])].sort((a,b) => {
    const sa = isV3 ? (a.score == null ? -1 : a.score) : (a.score == null ? -1 : a.score * 33.3);
    const sb = isV3 ? (b.score == null ? -1 : b.score) : (b.score == null ? -1 : b.score * 33.3);
    return sb - sa || (b.weight || 0) - (a.weight || 0);
  }).forEach(item => {
    const s = isV3 ? item.score : (item.score == null ? null : item.score * 33.3);
    const el = document.createElement("article");
    el.className = "card";
    el.style.setProperty("--accent", scoreColor(s));
    const source = item.source_url
      ? '<a href="'+esc(item.source_url)+'" target="_blank" rel="noreferrer">'+esc(item.source)+' ↗</a>'
      : esc(item.source);

    let components = "";
    const comp = item.components || {};
    const rows = [
      ["LEVEL", componentValue(comp.level), "45%"],
      ["DEVIATION", componentValue(comp.deviation), "30%"],
      ["VELOCITY", componentValue(comp.velocity), "25%"]
    ];
    if (rows.some(x => x[1] != null)) {
      components = '<div class="components">';
      rows.forEach(x => {
        components += '<div class="component-row"><span>'+x[0]+'</span><div class="component-track"><i style="width:'+(x[1] == null ? 0 : x[1])+'%"></i></div><b>'+(x[1] == null ? "—" : Math.round(x[1]))+'</b><em>'+x[2]+'</em></div>';
      });
      components += '</div>';
    }

    let stats = "";
    if (item.stats && (item.stats.percentile != null || item.stats.robust_z != null)) {
      stats = '<div class="stats">';
      if (item.stats.percentile != null) stats += '<span>PCTL '+esc(item.stats.percentile)+'</span>';
      if (item.stats.robust_z != null) stats += '<span>ROBUST Z '+esc(item.stats.robust_z)+'</span>';
      if (item.stats.velocity_pct_5 != null) stats += '<span>5D Δ PCTL '+esc(item.stats.velocity_pct_5)+'</span>';
      if (item.stats.velocity_pct_20 != null) stats += '<span>20D Δ PCTL '+esc(item.stats.velocity_pct_20)+'</span>';
      stats += '</div>';
    }

    el.innerHTML =
      '<div class="card-top"><div><h3>'+esc(item.name)+'</h3><span class="riskword">'+riskWord(s)+'</span></div><span class="mode">'+esc(item.mode)+'</span></div>'+
      '<div class="value">'+esc(item.value)+'</div>'+
      '<div class="scoreline"><strong>'+displayScore(s)+'</strong><span>/100</span><small>WEIGHT '+esc(item.weight || 0)+'%</small></div>'+
      '<div class="meta"><span>'+source+'</span><span>as of '+esc(item.as_of || "—")+'</span></div>'+
      components+stats+
      '<p class="note">'+esc(item.note)+'</p>';
    grid.appendChild(el);
  });

  const d = data.diagnostics || {};
  const diagItems = [
    ["US 10Y", d.us10y == null ? "—" : Number(d.us10y).toFixed(2)+"%"],
    ["US 2Y", d.us2y == null ? "—" : Number(d.us2y).toFixed(2)+"%"],
    ["2s10s", d.curve_2s10s_bps == null ? "—" : Number(d.curve_2s10s_bps).toFixed(0)+" bp"],
    ["VIX", d.vix == null ? "—" : Number(d.vix).toFixed(2)],
    ["10Y RV20", d.realized_10y_vol_bps == null ? "—" : Number(d.realized_10y_vol_bps).toFixed(0)+" bp ann."],
    ["MOVE", d.move_manual == null ? "manual未入力" : Number(d.move_manual).toFixed(1)],
    ["SOFR−IORB", d.sofr_iorb_bps == null ? "—" : Number(d.sofr_iorb_bps).toFixed(1)+" bp"],
    ["Financial CP−FF", d.cpff == null ? "—" : Number(d.cpff).toFixed(2)+"%"],
    ["CCC OAS", d.ccc_oas == null ? "—" : Number(d.ccc_oas).toFixed(2)+"%"],
    ["CDX HY", d.cdx_hy_bps == null ? "manual未入力" : Number(d.cdx_hy_bps).toFixed(0)+" bp"],
    ["CLO BBB", d.clo_bbb_bps == null ? "manual未入力" : Number(d.clo_bbb_bps).toFixed(0)+" bp"],
    ["Bank CDS", d.bank_cds_bps == null ? "manual未入力" : Number(d.bank_cds_bps).toFixed(0)+" bp"],
    ["BDC NAV disc.", d.bdc_discount_pct == null ? "manual未入力" : Number(d.bdc_discount_pct).toFixed(1)+"%"],
    ["Italy–Bund", d.italy_bund_bps == null ? "—" : Number(d.italy_bund_bps).toFixed(0)+" bp"],
    ["WTI", d.wti == null ? "—" : "$"+Number(d.wti).toFixed(2)]
  ];
  const diag = document.getElementById("diagnostics");
  diagItems.forEach(x => {
    const el=document.createElement("div");
    el.className="diag";
    el.innerHTML='<span>'+esc(x[0])+'</span><strong>'+esc(x[1])+'</strong>';
    diag.appendChild(el);
  });

  renderHistory(history);
  renderNeural(neural);
  renderBacktest(backtest);


  function renderNeural(nn){
    const scoreEl = document.getElementById("nnScore");
    if (!scoreEl) return;
    if (!nn) {
      for (const id of ["nnScore","nnUncertainty","nnHybrid","nnThreshold","nnValAuc","nnTestAuc","nnBrier","nnFpr"]) {
        const el=document.getElementById(id); if(el) el.textContent="pending";
      }
      return;
    }

    const cur = nn.current || {};
    const metrics = nn.metrics || {};
    const val = metrics.validation || {};
    const test = metrics.test_holdout || {};
    const testAt = test.at_selected_threshold || {};

    scoreEl.textContent = cur.production_nn_score == null ? "—" : Number(cur.production_nn_score).toFixed(1);
    scoreEl.style.color = scoreColor(cur.production_nn_score);
    document.getElementById("nnUncertainty").textContent = cur.production_uncertainty_std == null ? "—" : "±"+Number(cur.production_uncertainty_std).toFixed(1);
    document.getElementById("nnHybrid").textContent = cur.hybrid_market_score == null ? "—" : Number(cur.hybrid_market_score).toFixed(1);
    document.getElementById("nnThreshold").textContent = cur.threshold_score == null ? "—" : Number(cur.threshold_score).toFixed(1);
    document.getElementById("nnValAuc").textContent = val.roc_auc == null ? "—" : Number(val.roc_auc).toFixed(3);
    document.getElementById("nnTestAuc").textContent = test.roc_auc == null ? "—" : Number(test.roc_auc).toFixed(3);
    document.getElementById("nnBrier").textContent = test.brier == null ? "—" : Number(test.brier).toFixed(3);
    document.getElementById("nnFpr").textContent = testAt.false_positive_rate == null ? "—" : (Number(testAt.false_positive_rate)*100).toFixed(1)+"%";

    const drivers=document.getElementById("nnDrivers");
    (cur.top_local_sensitivities || []).forEach(d=>{
      const row=document.createElement("div");
      row.className="driver-row";
      const width=Math.min(100,Math.abs(Number(d.delta_score||0))*8);
      row.innerHTML='<span>'+esc(d.feature)+'</span><div class="driver-track"><i style="width:'+width+'%"></i></div><b>'+((Number(d.delta_score)>=0?"+":"")+Number(d.delta_score).toFixed(1))+'</b>';
      drivers.appendChild(row);
    });

    const events=document.getElementById("nnEvents");
    (nn.event_evaluation || []).forEach(ev=>{
      const row=document.createElement("div");
      row.className="nn-event";
      row.innerHTML='<span>'+esc(ev.name)+'</span><b>'+esc(ev.peak_nn_score==null?"—":Number(ev.peak_nn_score).toFixed(1))+'</b><small>'+esc(ev.first_alert||"no alert")+'</small>';
      events.appendChild(row);
    });
  }

  function renderBacktest(bt){
    const currentEl = document.getElementById("btCurrent");
    if (!currentEl) return;
    if (!bt) {
      currentEl.textContent = "pending";
      document.getElementById("btPercentile").textContent = "pending";
      document.getElementById("btOutsideRate").textContent = "pending";
      document.getElementById("btP95").textContent = "pending";
      document.getElementById("backtestChart").innerHTML = '<div style="padding:55px 18px;color:var(--muted);font-size:12px">v5 backtest data is being generated.</div>';
      return;
    }

    const cur = bt.current || {};
    const dist = bt.distribution || {};
    const audit = bt.alert_audit || {};
    const outside = audit.outside_labeled_windows_rate_pct || {};

    const comparable = cur.historical_comparable_score != null ? cur.historical_comparable_score : cur.market_score;
    currentEl.textContent = comparable == null ? "—" : Number(comparable).toFixed(1);
    document.getElementById("btPercentile").textContent = cur.percentile_outside_labeled_windows == null ? "—" : Number(cur.percentile_outside_labeled_windows).toFixed(1)+"%";
    document.getElementById("btOutsideRate").textContent = outside["45"] == null ? "—" : Number(outside["45"]).toFixed(1)+"%";
    document.getElementById("btP95").textContent = dist.outside_windows_p95 == null ? "—" : Number(dist.outside_windows_p95).toFixed(1);

    const rows = (bt.series || []).filter(r => r.score != null);
    const box = document.getElementById("backtestChart");
    if (rows.length) {
      const w=1000,h=200,pad=16;
      const xs=rows.map((_,i)=>rows.length===1?w/2:pad+i*(w-2*pad)/(rows.length-1));
      const ys=rows.map(r=>h-pad-(clamp(r.score)/100)*(h-2*pad));
      let path="";
      xs.forEach((x,i)=>{path+=(i?" L ":"M ")+x.toFixed(1)+" "+ys[i].toFixed(1)});
      const eventMarks=(bt.events || []).map(ev=>{
        if(!ev.max_score_date) return "";
        const idx=rows.findIndex(r=>r.date>=ev.max_score_date);
        if(idx<0) return "";
        return '<circle cx="'+xs[idx]+'" cy="'+ys[idx]+'" r="5" fill="'+scoreColor(ev.max_score)+'"><title>'+esc(ev.name)+' '+esc(ev.max_score)+'</title></circle>';
      }).join("");
      box.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-label="walk forward backtest">'+
        '<line x1="0" y1="'+(h-pad-(45/100)*(h-2*pad))+'" x2="'+w+'" y2="'+(h-pad-(45/100)*(h-2*pad))+'" stroke="#ff8b4c" stroke-width="1" stroke-dasharray="6 7" vector-effect="non-scaling-stroke"/>'+
        '<line x1="0" y1="'+(h-pad-(65/100)*(h-2*pad))+'" x2="'+w+'" y2="'+(h-pad-(65/100)*(h-2*pad))+'" stroke="#ff4f6d" stroke-width="1" stroke-dasharray="6 7" vector-effect="non-scaling-stroke"/>'+
        '<path d="'+path+'" fill="none" stroke="#72a7ff" stroke-width="3" vector-effect="non-scaling-stroke"/>'+eventMarks+'</svg>';
    } else {
      box.innerHTML='<div style="padding:55px 18px;color:var(--muted);font-size:12px">No backtest observations.</div>';
    }

    const body=document.getElementById("backtestEvents");
    (bt.events || []).forEach(ev=>{
      const tr=document.createElement("tr");
      const lead=ev.lead_days_elevated_vs_reference;
      tr.innerHTML='<td><strong>'+esc(ev.name)+'</strong><small>'+esc(ev.start)+' → '+esc(ev.end)+'</small></td>'+
        '<td>'+esc(ev.group)+'</td>'+
        '<td>'+ (ev.max_score==null?"—":Number(ev.max_score).toFixed(1)) +'<small>'+esc(ev.max_score_date||"—")+'</small></td>'+
        '<td>'+esc(ev.max_stage==null?"—":ev.max_stage)+'</td>'+
        '<td>'+esc(ev.first_elevated||"—")+'</td>'+
        '<td>'+ (lead==null?"—":(lead>=0?lead+"d early":Math.abs(lead)+"d after")) +'</td>';
      body.appendChild(tr);
    });
  }

  function renderHistory(rows){
    const box = document.getElementById("historyChart");
    const valid = rows.filter(r => r.score != null);
    if (!valid.length){
      box.innerHTML='<div style="padding:55px 18px;color:var(--muted);font-size:12px">履歴は更新ごとに蓄積されます。</div>';
      return;
    }
    const last=valid[valid.length-1];
    document.getElementById("historyLast").textContent = last.date+"  "+Math.round(last.score)+"/100";
    const w=1000,h=180,pad=16;
    const xs=valid.map((_,i)=>valid.length===1?w/2:pad+i*(w-2*pad)/(valid.length-1));
    const ys=valid.map(r=>h-pad-(clamp(r.score)/100)*(h-2*pad));
    let path="";
    xs.forEach((x,i)=>{path+=(i?" L ":"M ")+x.toFixed(1)+" "+ys[i].toFixed(1)});
    const circles=xs.map((x,i)=>'<circle cx="'+x+'" cy="'+ys[i]+'" r="'+(i===xs.length-1?6:3)+'" fill="'+scoreColor(valid[i].score)+'"/>').join("");
    const area=valid.length>1 ? path+' L '+xs[xs.length-1]+' '+(h-pad)+' L '+xs[0]+' '+(h-pad)+' Z' : "";
    box.innerHTML='<svg viewBox="0 0 '+w+' '+h+'" preserveAspectRatio="none" aria-label="stress history">'+
      (area?'<path d="'+area+'" fill="rgba(114,167,255,.08)"/>':'')+
      '<path d="'+path+'" fill="none" stroke="#72a7ff" stroke-width="4" vector-effect="non-scaling-stroke"/>'+circles+
      '</svg>';
  }
})();
