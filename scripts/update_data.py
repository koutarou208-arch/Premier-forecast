#!/usr/bin/env python3
import csv, io, json, math, pathlib, urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "manual.json"
OUTPUT = ROOT / "data" / "latest.js"

SERIES = {
    "ig_oas": "BAMLC0A0CM",
    "hy_oas": "BAMLH0A0HYM2",
    "stlfsi": "STLFSI4",
    "vix": "VIXCLS",
    "wti": "DCOILWTICO",
    "gas": "DHHNGSP",
}

def fetch_latest(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "crisis-watch/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        text = r.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    for row in reversed(rows[1:]):
        if len(row) >= 2 and row[1] not in ("", "."):
            return float(row[1]), row[0]
    raise RuntimeError(f"No value for {series_id}")

def asc_score(value, t1, t2, t3):
    if value is None: return 0
    if value < t1: return 0
    if value < t2: return 1
    if value < t3: return 2
    return 3

def safe_fetch(name, failures):
    try:
        v, d = fetch_latest(SERIES[name])
        return {"value": v, "date": d}
    except Exception as e:
        failures.append(f"{name}: {e}")
        return {"value": None, "date": None}

def fmt(v, suffix="", digits=2):
    return "N/A" if v is None else f"{v:.{digits}f}{suffix}"

def level(score):
    if score < 25: return "NORMAL"
    if score < 45: return "WATCH"
    if score < 65: return "ELEVATED"
    if score < 80: return "HIGH"
    return "CRITICAL"

def main():
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    failures = []
    x = {k: safe_fetch(k, failures) for k in SERIES}

    ig = x["ig_oas"]["value"]
    hy = x["hy_oas"]["value"]
    stlfsi = x["stlfsi"]["value"]
    vix = x["vix"]["value"]
    wti = x["wti"]["value"]
    gas = x["gas"]["value"]

    ig_score = asc_score(ig, 1.00, 1.50, 2.50)
    hy_score = asc_score(hy, 4.00, 6.00, 9.00)
    stlfsi_score = asc_score(stlfsi, 0.00, 1.00, 2.00)
    vix_score = asc_score(vix, 20.00, 30.00, 40.00)
    treasury_score = max(stlfsi_score, vix_score)
    wti_score = asc_score(wti, 100.00, 130.00, 160.00)
    gas_score = asc_score(gas, 5.00, 8.00, 12.00)
    energy_score = max(wti_score, gas_score)

    dc_score = int(manual["data_center_financing"]["score"])
    pc_score = int(manual["private_credit"]["score"])
    bank_score = int(manual["bank_ai_inventory"]["score"])
    eu_bps = float(manual["europe_sovereign_spread_bps"]["value"])
    eu_score = asc_score(eu_bps, 150, 250, 400)

    scores = [ig_score, dc_score, pc_score, bank_score, hy_score, treasury_score, eu_score, energy_score]
    total = round(sum(scores) / (3 * len(scores)) * 100, 1)
    lvl = level(total)
    reds = sum(s == 3 for s in scores)
    oranges = sum(s == 2 for s in scores)

    if failures:
        summary = f"{lvl}: {len(failures)} automatic source(s) unavailable; verify data quality before interpretation."
    elif reds >= 2 or (reds >= 1 and oranges >= 2):
        summary = f"{lvl}: stress is broadening across multiple channels. Focus on credit-market transmission, not equity moves alone."
    elif total >= 25:
        summary = f"{lvl}: multiple channels are moving away from normal. Watch for simultaneous spread widening and funding impairment."
    else:
        summary = "No broad credit-freeze signal in the latest composite. Continue watching structural AI/private-credit channels for transmission."

    indicators = [
      {"id":"ai_credit","name":"AI corporate credit proxy","score":ig_score,"value":fmt(ig,"%"),"source":"FRED BAMLC0A0CM","mode":"AUTO","note":"Broad US IG OAS proxy; not AI-specific."},
      {"id":"data_center","name":"Data-center financing","score":dc_score,"value":"Manual","source":"Deal / lender evidence","mode":"MANUAL","note":manual["data_center_financing"]["note"]},
      {"id":"private_credit","name":"Private-credit liquidity","score":pc_score,"value":"Manual","source":"Fund disclosures / reporting","mode":"MANUAL","note":manual["private_credit"]["note"]},
      {"id":"bank_ai","name":"Bank AI-credit inventory","score":bank_score,"value":"Manual","source":"Bank / syndication evidence","mode":"MANUAL","note":manual["bank_ai_inventory"]["note"]},
      {"id":"hy","name":"US High Yield OAS","score":hy_score,"value":fmt(hy,"%"),"source":"FRED BAMLH0A0HYM2","mode":"AUTO","note":"Broad speculative-grade credit stress."},
      {"id":"treasury","name":"Treasury liquidity / volatility proxy","score":treasury_score,"value":f"STLFSI {fmt(stlfsi,'',2)} / VIX {fmt(vix,'',2)}","source":"FRED STLFSI4 + VIXCLS","mode":"AUTO","note":"Proxy only; does not directly measure Treasury bid-ask depth."},
      {"id":"europe","name":"Europe sovereign spread","score":eu_score,"value":f"{eu_bps:.0f} bp","source":"Manual Italy-Bund style spread","mode":"MANUAL","note":manual["europe_sovereign_spread_bps"]["note"]},
      {"id":"energy","name":"Energy shock","score":energy_score,"value":f"WTI {fmt(wti,'',2)} / Henry Hub {fmt(gas,'',2)}","source":"FRED DCOILWTICO + DHHNGSP","mode":"AUTO","note":"Composite uses the more severe of oil and gas stress scores."}
    ]

    payload = {
      "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
      "score": total,
      "level": lvl,
      "summary": summary,
      "data_failures": failures,
      "indicators": indicators
    }
    OUTPUT.write_text("window.__RISK_DATA__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    print(json.dumps({"score": total, "level": lvl, "failures": failures}, ensure_ascii=False))

if __name__ == "__main__":
    main()
