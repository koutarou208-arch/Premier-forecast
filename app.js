(() => {
  const data = window.__RISK_DATA__;
  if (!data) return;

  const names = ["NORMAL","WATCH","ELEVATED","HIGH","CRITICAL"];
  const color = score => score <= 0 ? "var(--s0)" : score === 1 ? "var(--s1)" : score === 2 ? "var(--s2)" : "var(--s3)";
  const riskWord = score => ["NORMAL","WATCH","HIGH","SEVERE"][Math.max(0, Math.min(3, score))];

  document.getElementById("score").textContent = Math.round(data.score);
  document.getElementById("level").textContent = data.level;
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("updated").textContent = "Updated " + new Date(data.updated_at).toLocaleString("ja-JP", {timeZone:"Asia/Tokyo"});
  const ring = document.getElementById("scoreRing");
  ring.style.setProperty("--p", Math.min(100, Math.max(0, data.score)));
  const overallAccent = data.score < 25 ? "var(--s0)" : data.score < 45 ? "var(--s1)" : data.score < 65 ? "var(--s2)" : "var(--s3)";
  ring.style.setProperty("--accent", overallAccent);
  document.getElementById("level").style.color = overallAccent;

  const grid = document.getElementById("grid");
  [...data.indicators].sort((a,b) => b.score - a.score).forEach(item => {
    const el = document.createElement("article");
    el.className = "card";
    el.style.setProperty("--accent", color(item.score));
    const bars = [1,2,3].map(n => `<i class="${item.score >= n ? "on" : ""}"></i>`).join("");
    el.innerHTML = `
      <div class="card-top">
        <div><h3>${item.name}</h3><span class="riskword">${riskWord(item.score)}</span></div>
        <span class="mode">${item.mode}</span>
      </div>
      <div class="value">${item.value}</div>
      <div class="meta">${item.source}</div>
      <p class="note">${item.note}</p>
      <div class="riskline"><div class="bars">${bars}</div><span class="riskword">${item.score}/3</span></div>`;
    grid.appendChild(el);
  });
})();
