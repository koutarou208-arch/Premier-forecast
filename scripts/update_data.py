#!/usr/bin/env python3
import csv
import io
import json
import math
import pathlib
import statistics
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANUAL = ROOT / "data" / "manual.json"
OUTPUT = ROOT / "data" / "latest.js"
HISTORY_JSON = ROOT / "data" / "history.json"
HISTORY_JS = ROOT / "data" / "history.js"

SERIES = {
    "ig_oas": "BAMLC0A0CM",
    "hy_oas": "BAMLH0A0HYM2",
    "stlfsi": "STLFSI4",
    "vix": "VIXCLS",
    "wti": "DCOILWTICO",
    "gas": "DHHNGSP",
    "dgs10": "DGS10",
    "dgs2": "DGS2",
    "italy10": "IRLTLT01ITM156N",
    "germany10": "IRLTLT01DEM156N",
}

WEIGHTS = {
    "ig_credit": 12,
    "hy_credit": 18,
    "financial_stress": 10,
    "rates_liquidity": 10,
    "europe": 10,
    "energy": 10,
    "data_center": 10,
    "private_credit": 12,
    "bank_ai": 8,
}

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

def fetch_series(series_id):
    req = urllib.request.Request(
        FRED_URL.format(series_id=series_id),
        headers={"User-Agent": "global-financial-crisis-watch-v2/2.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode("utf-8")
    rows = list(csv.reader(io.StringIO(text)))
    result = []
    for row in rows[1:]:
        if len(row) >= 2 and row[1] not in ("", "."):
            try:
                result.append((row[0], float(row[1])))
            except ValueError:
                pass
    if not result:
        raise RuntimeError(f"No observations for {series_id}")
    return result

def safe_series(name, failures):
    try:
        return fetch_series(SERIES[name])
    except Exception as e:
        failures.append(f"{name}: {e}")
        return []

def latest(series):
    return series[-1] if series else (None, None)

def asc_score(value, t1, t2, t3):
    if value is None:
        return 0
    if value < t1:
        return 0
    if value < t2:
        return 1
    if value < t3:
        return 2
    return 3

def common_spread(a, b):
    ma = dict(a)
    mb = dict(b)
    common = sorted(set(ma).intersection(mb))
    if not common:
        return None, None
    d = common[-1]
    return (ma[d] - mb[d]) * 100.0, d

def realized_yield_vol_bps(series, window=20):
    vals = [v for _, v in series[-(window + 1):]]
    if len(vals) < 6:
        return None
    changes_bps = [(vals[i] - vals[i - 1]) * 100.0 for i in range(1, len(vals))]
    if len(changes_bps) < 2:
        return None
    return statistics.stdev(changes_bps) * math.sqrt(252.0)

def fmt(v, suffix="", digits=2):
    return "N/A" if v is None else f"{v:.{digits}f}{suffix}"

def level(score):
    if score < 25:
        return "NORMAL"
    if score < 45:
        return "WATCH"
    if score < 65:
        return "ELEVATED"
    if score < 80:
        return "HIGH"
    return "CRITICAL"

def weighted_score(items):
    num = 0.0
    den = 0.0
    for key, score in items.items():
        w = WEIGHTS[key]
        num += (score / 3.0) * 100.0 * w
        den += w
    return round(num / den, 1) if den else 0.0

def pillar_score(scores, keys):
    if not keys:
        return 0.0
    return round(sum(scores[k] for k in keys) / (3.0 * len(keys)) * 100.0, 1)

def transmission_stage(scores):
    structural = (scores["data_center"] + scores["private_credit"] + scores["bank_ai"]) / 3.0
    core_credit = max(scores["ig_credit"], scores["hy_credit"])
    liquidity = max(scores["financial_stress"], scores["rates_liquidity"])

    if core_credit >= 3 and liquidity >= 3:
        return 4, "SYSTEMIC / FREEZE", "Broad credit and funding markets are simultaneously in severe stress."
    if core_credit >= 2 and liquidity >= 2:
        return 3, "FUNDING STRESS", "Sector stress has propagated into broad credit and market liquidity."
    if structural >= 1.5 and core_credit >= 1:
        return 2, "CREDIT TRANSMISSION", "AI/private-credit stress is now accompanied by broader credit repricing."
    if structural >= 1.0:
        return 1, "SECTOR REPRICING", "AI infrastructure/private-credit channels show stress, but broad credit transmission is not confirmed."
    return 0, "CALM", "No material sector-to-system transmission signal."

def make_flags(scores, energy_score, europe_score):
    flags = []
    if max(scores["data_center"], scores["private_credit"], scores["bank_ai"]) >= 2:
        flags.append({"type": "AI_CREDIT", "label": "AI / Private Credit stress is material"})
    if scores["hy_credit"] >= 2 or scores["ig_credit"] >= 2:
        flags.append({"type": "CREDIT", "label": "Broad corporate credit spreads are stressed"})
    if scores["rates_liquidity"] >= 2 or scores["financial_stress"] >= 2:
        flags.append({"type": "LIQUIDITY", "label": "Market liquidity / volatility is stressed"})
    if europe_score >= 2:
        flags.append({"type": "EUROPE", "label": "Euro sovereign fragmentation is elevated"})
    if energy_score >= 2:
        flags.append({"type": "ENERGY", "label": "Energy shock is large enough to constrain policy"})
    if energy_score >= 2 and max(scores["ig_credit"], scores["hy_credit"]) >= 1:
        flags.append({"type": "COMPOUND", "label": "Energy + credit compound shock"})
    if not flags:
        flags.append({"type": "CLEAR", "label": "No cross-market contagion trigger"})
    return flags

def load_history():
    if not HISTORY_JSON.exists():
        return []
    try:
        data = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def save_history(history, record):
    day = record["date"]
    history = [x for x in history if x.get("date") != day]
    history.append(record)
    history = sorted(history, key=lambda x: x.get("date", ""))[-365:]
    HISTORY_JSON.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    HISTORY_JS.write_text(
        "window.__RISK_HISTORY__ = " + json.dumps(history, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

def main():
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    failures = []
    series = {k: safe_series(k, failures) for k in SERIES}

    dates = {}
    values = {}
    for k, s in series.items():
        d, v = latest(s)
        dates[k] = d
        values[k] = v

    ig = values["ig_oas"]
    hy = values["hy_oas"]
    stlfsi = values["stlfsi"]
    vix = values["vix"]
    wti = values["wti"]
    gas = values["gas"]
    dgs10 = values["dgs10"]
    dgs2 = values["dgs2"]

    ig_score = asc_score(ig, 1.00, 1.50, 2.50)
    hy_score = asc_score(hy, 4.00, 6.00, 9.00)
    stlfsi_score = asc_score(stlfsi, 0.00, 1.00, 2.00)
    vix_score = asc_score(vix, 20.00, 30.00, 40.00)

    realized_vol = realized_yield_vol_bps(series["dgs10"], 20)
    realized_score = asc_score(realized_vol, 80.0, 110.0, 150.0)
    move_manual = manual.get("move_index", {}).get("value")
    move_score = asc_score(float(move_manual), 90.0, 120.0, 160.0) if move_manual is not None else 0
    rates_score = max(realized_score, move_score, vix_score)

    italy_bund_bps, italy_bund_date = common_spread(series["italy10"], series["germany10"])
    europe_override = manual.get("europe_daily_spread_bps", {}).get("value")
    europe_bps = float(europe_override) if europe_override is not None else italy_bund_bps
    europe_score = asc_score(europe_bps, 150.0, 250.0, 400.0)

    wti_score = asc_score(wti, 100.0, 130.0, 160.0)
    gas_score = asc_score(gas, 5.0, 8.0, 12.0)
    energy_score = max(wti_score, gas_score)

    dc_score = int(manual["data_center_financing"]["score"])
    pc_score = int(manual["private_credit"]["score"])
    bank_score = int(manual["bank_ai_inventory"]["score"])

    scores = {
        "ig_credit": ig_score,
        "hy_credit": hy_score,
        "financial_stress": stlfsi_score,
        "rates_liquidity": rates_score,
        "europe": europe_score,
        "energy": energy_score,
        "data_center": dc_score,
        "private_credit": pc_score,
        "bank_ai": bank_score,
    }

    total = weighted_score(scores)
    lvl = level(total)
    stage, stage_label, stage_note = transmission_stage(scores)
    flags = make_flags(scores, energy_score, europe_score)

    pillars = [
        {"name": "Broad Credit", "score": pillar_score(scores, ["ig_credit", "hy_credit"])},
        {"name": "Funding / Liquidity", "score": pillar_score(scores, ["financial_stress", "rates_liquidity"])},
        {"name": "AI / Private Credit", "score": pillar_score(scores, ["data_center", "private_credit", "bank_ai"])},
        {"name": "Europe / Energy", "score": pillar_score(scores, ["europe", "energy"])},
    ]

    if failures:
        summary = f"{lvl}: {len(failures)} automatic source(s) failed. Composite is usable only after checking data quality."
    elif stage >= 3:
        summary = f"{lvl}: broad credit and liquidity transmission is visible. This is no longer only an AI-sector repricing signal."
    elif stage == 2:
        summary = f"{lvl}: structural AI/private-credit stress is beginning to overlap with broader credit repricing."
    elif stage == 1:
        summary = f"{lvl}: AI infrastructure/private-credit stress is material, but broad market contagion is not yet confirmed."
    else:
        summary = f"{lvl}: no material sector-to-system transmission signal."

    curve = None
    if dgs10 is not None and dgs2 is not None:
        curve = (dgs10 - dgs2) * 100.0

    indicators = [
        {
            "id": "ig_credit", "name": "US IG Corporate OAS", "score": ig_score,
            "value": fmt(ig, "%"), "source": "FRED BAMLC0A0CM", "mode": "AUTO",
            "as_of": dates["ig_oas"], "weight": WEIGHTS["ig_credit"],
            "source_url": "https://fred.stlouisfed.org/series/BAMLC0A0CM",
            "note": "Broad investment-grade spread. AI-specific stress should eventually appear here if contagion broadens."
        },
        {
            "id": "hy_credit", "name": "US High Yield OAS", "score": hy_score,
            "value": fmt(hy, "%"), "source": "FRED BAMLH0A0HYM2", "mode": "AUTO",
            "as_of": dates["hy_oas"], "weight": WEIGHTS["hy_credit"],
            "source_url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
            "note": "Core contagion indicator. A sustained move through 6-9% OAS would be materially different from an equity-only correction."
        },
        {
            "id": "financial_stress", "name": "St. Louis Financial Stress", "score": stlfsi_score,
            "value": fmt(stlfsi, "", 2), "source": "FRED STLFSI4", "mode": "AUTO",
            "as_of": dates["stlfsi"], "weight": WEIGHTS["financial_stress"],
            "source_url": "https://fred.stlouisfed.org/series/STLFSI4",
            "note": "Cross-market financial stress proxy. Positive and rising values signal stress above normal conditions."
        },
        {
            "id": "rates_liquidity", "name": "Treasury Vol / Liquidity", "score": rates_score,
            "value": f"RV20 {fmt(realized_vol, ' bp')} / VIX {fmt(vix)}" + (f" / MOVE {fmt(float(move_manual))}" if move_manual is not None else ""),
            "source": "FRED DGS10 + VIXCLS" + (" + manual MOVE" if move_manual is not None else ""),
            "mode": "HYBRID" if move_manual is not None else "AUTO",
            "as_of": dates["dgs10"], "weight": WEIGHTS["rates_liquidity"],
            "source_url": "https://fred.stlouisfed.org/series/DGS10",
            "note": "RV20 is annualized 20-day realized volatility of daily 10Y Treasury yield changes. It is a MOVE-like proxy, not the MOVE index itself."
        },
        {
            "id": "europe", "name": "Italy-Bund 10Y Spread", "score": europe_score,
            "value": fmt(europe_bps, " bp", 0), "source": "OECD via FRED" if europe_override is None else "Manual daily override",
            "mode": "AUTO-MONTHLY" if europe_override is None else "HYBRID",
            "as_of": italy_bund_date if europe_override is None else manual.get("europe_daily_spread_bps", {}).get("as_of"),
            "weight": WEIGHTS["europe"],
            "source_url": "https://fred.stlouisfed.org/graph/?g=j3d3",
            "note": "Exact Italy minus Germany 10Y benchmark spread using common-date OECD/FRED observations. Monthly unless manually overridden with a current daily spread."
        },
        {
            "id": "energy", "name": "Energy Shock", "score": energy_score,
            "value": f"WTI {fmt(wti, '$', 2)} / Henry Hub {fmt(gas, '$', 2)}",
            "source": "FRED DCOILWTICO + DHHNGSP", "mode": "AUTO",
            "as_of": max([d for d in [dates["wti"], dates["gas"]] if d] or [None]),
            "weight": WEIGHTS["energy"],
            "source_url": "https://fred.stlouisfed.org/series/DCOILWTICO",
            "note": "Uses the more severe oil/gas stress score. High energy stress can limit the ability of central banks to cushion a credit shock."
        },
        {
            "id": "data_center", "name": "AI Data-center Financing", "score": dc_score,
            "value": "Event score", "source": "Reuters / deal evidence", "mode": "EVENT",
            "as_of": manual["data_center_financing"].get("as_of"), "weight": WEIGHTS["data_center"],
            "source_url": manual["data_center_financing"].get("source_url"),
            "note": manual["data_center_financing"]["note"]
        },
        {
            "id": "private_credit", "name": "Private-credit Liquidity", "score": pc_score,
            "value": "Event score", "source": "Fund disclosures / Reuters", "mode": "EVENT",
            "as_of": manual["private_credit"].get("as_of"), "weight": WEIGHTS["private_credit"],
            "source_url": manual["private_credit"].get("source_url"),
            "note": manual["private_credit"]["note"]
        },
        {
            "id": "bank_ai", "name": "Bank AI-credit Inventory", "score": bank_score,
            "value": "Event score", "source": "Syndication / lender evidence", "mode": "EVENT",
            "as_of": manual["bank_ai_inventory"].get("as_of"), "weight": WEIGHTS["bank_ai"],
            "source_url": manual["bank_ai_inventory"].get("source_url"),
            "note": manual["bank_ai_inventory"]["note"]
        },
    ]

    diagnostics = {
        "us10y": dgs10,
        "us2y": dgs2,
        "curve_2s10s_bps": curve,
        "vix": vix,
        "realized_10y_vol_bps": realized_vol,
        "move_manual": move_manual,
        "italy_bund_bps": europe_bps,
        "italy_bund_frequency": "manual daily" if europe_override is not None else "monthly",
        "wti": wti,
        "gas": gas,
    }

    now = datetime.now(timezone.utc)
    payload = {
        "version": 2,
        "updated_at": now.isoformat().replace("+00:00", "Z"),
        "score": total,
        "level": lvl,
        "summary": summary,
        "transmission": {"stage": stage, "label": stage_label, "note": stage_note},
        "flags": flags,
        "pillars": pillars,
        "weights": WEIGHTS,
        "diagnostics": diagnostics,
        "data_failures": failures,
        "indicators": indicators,
    }

    OUTPUT.write_text(
        "window.__RISK_DATA__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    history = load_history()
    save_history(history, {
        "date": now.date().isoformat(),
        "score": total,
        "level": lvl,
        "stage": stage,
        "pillars": {x["name"]: x["score"] for x in pillars},
        "hy_oas": hy,
        "ig_oas": ig,
        "stlfsi": stlfsi,
        "rates_vol": realized_vol,
        "italy_bund_bps": europe_bps,
        "wti": wti,
    })

    print(json.dumps({
        "version": 2,
        "score": total,
        "level": lvl,
        "stage": stage,
        "failures": failures,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
