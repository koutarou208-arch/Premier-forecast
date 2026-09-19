#!/usr/bin/env python3
import csv
import io
import json
import math
import pathlib
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date

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
    "sofr": "SOFR",
    "iorb": "IORB",
    "cpff": "CPFF",
    "ccc_oas": "BAMLH0A3HYC",
}

WEIGHTS = {
    "ig_credit": 10,
    "hy_credit": 14,
    "leveraged_credit": 10,
    "financial_stress": 8,
    "rates_liquidity": 8,
    "funding_market": 10,
    "banking_stress": 8,
    "europe": 6,
    "energy": 7,
    "data_center": 6,
    "private_credit": 8,
    "bank_ai": 5,
}

ABS_THRESHOLDS = {
    "ig_credit": (1.00, 1.50, 2.50),
    "hy_credit": (4.00, 6.00, 9.00),
    "financial_stress": (0.00, 1.00, 2.00),
    "rates_liquidity": (80.0, 110.0, 150.0),
    "funding_market": (5.0, 15.0, 30.0),
    "banking_cpff": (0.30, 0.75, 1.50),
    "leveraged_ccc": (8.0, 12.0, 20.0),
    "europe": (150.0, 250.0, 400.0),
    "energy_oil": (100.0, 130.0, 160.0),
    "energy_gas": (5.0, 8.0, 12.0),
}

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd={start_date}"
LOOKBACK = 1260

def fetch_series(series_id, start_date="2018-01-01"):
    req = urllib.request.Request(
        FRED_URL.format(series_id=series_id, start_date=start_date),
        headers={"User-Agent": "global-financial-crisis-watch-v5/5.0"},
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

def safe_series(name, failures, start_date="2018-01-01"):
    try:
        return fetch_series(SERIES[name], start_date=start_date)
    except Exception as e:
        failures.append(f"{name}: {e}")
        return []

def fetch_all_series(failures, max_workers=6, start_date="2018-01-01"):
    out = {k: [] for k in SERIES}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(fetch_series, sid, start_date): name for name, sid in SERIES.items()}
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                out[name] = fut.result()
            except Exception as e:
                failures.append(f"{name}: {e}")
                out[name] = []
    return out

def latest(series):
    return series[-1] if series else (None, None)

def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def pct_rank(sample, x, higher_is_risk=True):
    if x is None or not sample:
        return None
    ordered = sorted(sample)
    le = sum(1 for v in ordered if v <= x)
    p = 100.0 * le / len(ordered)
    return p if higher_is_risk else 100.0 - p

def median_mad(sample):
    if not sample:
        return None, None
    med = statistics.median(sample)
    dev = [abs(v - med) for v in sample]
    return med, statistics.median(dev)

def robust_z(sample, x, higher_is_risk=True):
    if x is None or len(sample) < 10:
        return None
    med, mad = median_mad(sample)
    if mad is None or mad == 0:
        sd = statistics.pstdev(sample)
        if sd == 0:
            return 0.0
        z = (x - med) / sd
    else:
        z = (x - med) / (1.4826 * mad)
    return z if higher_is_risk else -z

def tail_score_from_percentile(p, start=65.0):
    if p is None:
        return None
    if p <= start:
        return 0.0
    return clamp((p - start) / (100.0 - start) * 100.0)

def z_score_to_risk(z):
    if z is None:
        return None
    if z <= 0.5:
        return 0.0
    if z >= 3.0:
        return 100.0
    return (z - 0.5) / 2.5 * 100.0

def absolute_anchor(value, thresholds):
    if value is None:
        return None
    t1, t2, t3 = thresholds
    if value <= t1:
        return 0.0
    if value <= t2:
        return 33.3 * (value - t1) / (t2 - t1)
    if value <= t3:
        return 33.3 + 33.4 * (value - t2) / (t3 - t2)
    span = max(t3 - t2, 1e-9)
    return clamp(66.7 + 33.3 * (value - t3) / span)

def historical_delta_percentile(values, horizon, current_delta, higher_is_risk=True, lookback=LOOKBACK):
    if current_delta is None or len(values) <= horizon + 5:
        return None
    start = max(horizon, len(values) - lookback)
    deltas = [values[i] - values[i - horizon] for i in range(start, len(values))]
    return pct_rank(deltas[:-1] if len(deltas) > 1 else deltas, current_delta, higher_is_risk)

def dynamic_metric(series, absolute_value, thresholds, higher_is_risk=True, short=5, medium=20, lookback=LOOKBACK):
    if absolute_value is None or not series:
        return None
    values = [v for _, v in series]
    sample = values[-lookback:-1] if len(values) > 20 else values[:-1]
    if len(sample) < 10:
        return None

    anchor = absolute_anchor(absolute_value, thresholds)
    p = pct_rank(sample, absolute_value, higher_is_risk)
    z = robust_z(sample, absolute_value, higher_is_risk)
    deviation = max(tail_score_from_percentile(p), z_score_to_risk(z))

    def delta(h):
        if len(values) <= h:
            return None
        raw = values[-1] - values[-1-h]
        return raw if higher_is_risk else -raw

    d_short = delta(short)
    d_medium = delta(medium)
    p_short = historical_delta_percentile(values, short, d_short, True, lookback=lookback)
    p_medium = historical_delta_percentile(values, medium, d_medium, True, lookback=lookback)
    velocity = max(
        tail_score_from_percentile(p_short, 70.0) or 0.0,
        tail_score_from_percentile(p_medium, 70.0) or 0.0,
    )

    score = clamp(0.45 * anchor + 0.30 * deviation + 0.25 * velocity)
    return {
        "score": round(score, 1),
        "components": {
            "level": round(anchor, 1),
            "deviation": round(deviation, 1),
            "velocity": round(velocity, 1),
        },
        "stats": {
            "percentile": None if p is None else round(p, 1),
            "robust_z": None if z is None else round(z, 2),
            "delta_5": None if d_short is None else round(d_short, 4),
            "delta_20": None if d_medium is None else round(d_medium, 4),
            "velocity_pct_5": None if p_short is None else round(p_short, 1),
            "velocity_pct_20": None if p_medium is None else round(p_medium, 1),
        }
    }

def realized_yield_vol_series(series, window=20):
    out = []
    vals = [(d, v) for d, v in series]
    if len(vals) < window + 2:
        return out
    for i in range(window, len(vals)):
        changes_bps = [(vals[j][1] - vals[j-1][1]) * 100.0 for j in range(i-window+1, i+1)]
        if len(changes_bps) >= 2:
            out.append((vals[i][0], statistics.stdev(changes_bps) * math.sqrt(252.0)))
    return out

def common_spread_series(a, b):
    ma = dict(a)
    mb = dict(b)
    common = sorted(set(ma).intersection(mb))
    return [(d, (ma[d] - mb[d]) * 100.0) for d in common]

def event_adjusted_score(entry, today):
    raw = entry.get("score")
    if raw is None:
        return None, {}
    base = clamp(float(raw) / 3.0 * 100.0)
    conf = str(entry.get("confidence", "medium")).lower()
    conf_mult = {"high": 1.0, "medium": 0.85, "low": 0.70}.get(conf, 0.85)
    age_days = None
    freshness_mult = 1.0
    as_of = entry.get("as_of")
    if as_of:
        try:
            d = date.fromisoformat(as_of)
            age_days = max(0, (today - d).days)
            if age_days > 180:
                freshness_mult = 0.15
            elif age_days > 90:
                freshness_mult = 0.40
            elif age_days > 60:
                freshness_mult = 0.65
            elif age_days > 30:
                freshness_mult = 0.85
        except ValueError:
            freshness_mult = 0.70
    adjusted = round(base * conf_mult * freshness_mult, 1)
    return adjusted, {
        "raw_score_0_3": raw,
        "confidence": conf,
        "confidence_multiplier": conf_mult,
        "age_days": age_days,
        "freshness_multiplier": freshness_mult,
    }

def weighted_average(scores):
    num = den = 0.0
    for key, score in scores.items():
        if score is None:
            continue
        w = WEIGHTS[key]
        num += score * w
        den += w
    return (round(num / den, 1) if den else None, round(den, 1))

def pillar_score(scores, keys):
    vals = [scores[k] for k in keys if scores.get(k) is not None]
    return round(sum(vals) / len(vals), 1) if vals else None

def score_level(score):
    if score is None:
        return "NO DATA"
    if score < 25:
        return "NORMAL"
    if score < 45:
        return "WATCH"
    if score < 65:
        return "ELEVATED"
    if score < 80:
        return "HIGH"
    return "CRITICAL"

def breadth_overlay(scores):
    market_keys = [
        "ig_credit", "hy_credit", "leveraged_credit", "financial_stress",
        "rates_liquidity", "funding_market", "banking_stress", "europe", "energy"
    ]
    available = [scores[k] for k in market_keys if scores.get(k) is not None]
    if not available:
        return {"score": None, "stressed": 0, "available": 0, "severe": 0}
    stressed = sum(v >= 45 for v in available)
    severe = sum(v >= 65 for v in available)
    return {
        "score": round(100.0 * stressed / len(available), 1),
        "stressed": stressed,
        "available": len(available),
        "severe": severe
    }

def synchronized_bonus(breadth):
    if not breadth or breadth["available"] < 6:
        return 0.0
    if breadth["severe"] >= 6:
        return 8.0
    if breadth["stressed"] >= 6:
        return 5.0
    if breadth["stressed"] >= 4:
        return 2.5
    return 0.0

def transmission_stage(scores, breadth):
    structural = pillar_score(scores, ["data_center", "private_credit", "bank_ai"]) or 0.0
    credit = pillar_score(scores, ["ig_credit", "hy_credit", "leveraged_credit"]) or 0.0
    funding = pillar_score(scores, ["financial_stress", "rates_liquidity", "funding_market"]) or 0.0
    banking = pillar_score(scores, ["banking_stress", "bank_ai"]) or 0.0
    breadth_score = (breadth or {}).get("score") or 0.0

    if credit >= 75 and funding >= 70 and banking >= 60 and breadth_score >= 65:
        return 4, "SYSTEMIC / FREEZE", "Credit, funding and banking channels are simultaneously in severe, synchronized stress."
    if credit >= 55 and funding >= 50 and (banking >= 45 or breadth_score >= 50):
        return 3, "FUNDING STRESS", "Broad credit repricing is overlapping with funding-market and banking stress."
    if credit >= 40 and (structural >= 45 or banking >= 40 or breadth_score >= 35):
        return 2, "CREDIT TRANSMISSION", "Stress has moved beyond a single sector into broad and leveraged corporate credit."
    if structural >= 35 or banking >= 35:
        return 1, "SECTOR REPRICING", "AI/private-credit or banking channels are stressed, but broad contagion is not confirmed."
    return 0, "CALM", "No material sector-to-system transmission signal."

def load_history():
    if not HISTORY_JSON.exists():
        return []
    try:
        x = json.loads(HISTORY_JSON.read_text(encoding="utf-8"))
        return x if isinstance(x, list) else []
    except Exception:
        return []

def save_history(history, record):
    history = [x for x in history if x.get("date") != record["date"]]
    history.append(record)
    history = sorted(history, key=lambda x: x.get("date", ""))[-365:]
    HISTORY_JSON.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    HISTORY_JS.write_text("window.__RISK_HISTORY__ = " + json.dumps(history, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")

def fmt(v, suffix="", digits=2):
    return "N/A" if v is None else f"{v:.{digits}f}{suffix}"

def comp_or_empty(metric):
    return metric["components"] if metric else {"level": None, "deviation": None, "velocity": None}

def main():
    now = datetime.now(timezone.utc)
    today = now.date()
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    failures = []
    series = fetch_all_series(failures)
    latests = {k: latest(s) for k, s in series.items()}

    ig_d, ig = latests["ig_oas"]
    hy_d, hy = latests["hy_oas"]
    fs_d, stlfsi = latests["stlfsi"]
    vix_d, vix = latests["vix"]
    wti_d, wti = latests["wti"]
    gas_d, gas = latests["gas"]
    d10_d, dgs10 = latests["dgs10"]
    d2_d, dgs2 = latests["dgs2"]
    sofr_d, sofr = latests["sofr"]
    iorb_d, iorb = latests["iorb"]
    cpff_d, cpff = latests["cpff"]
    ccc_d, ccc_oas = latests["ccc_oas"]

    ig_m = dynamic_metric(series["ig_oas"], ig, ABS_THRESHOLDS["ig_credit"])
    hy_m = dynamic_metric(series["hy_oas"], hy, ABS_THRESHOLDS["hy_credit"])
    fs_m = dynamic_metric(series["stlfsi"], stlfsi, ABS_THRESHOLDS["financial_stress"], short=4, medium=13, lookback=260)

    sofr_iorb_series = common_spread_series(series["sofr"], series["iorb"])
    sofr_iorb_d, sofr_iorb_bps = latest(sofr_iorb_series)
    funding_m = dynamic_metric(sofr_iorb_series, sofr_iorb_bps, ABS_THRESHOLDS["funding_market"]) if sofr_iorb_bps is not None else None

    cpff_m = dynamic_metric(series["cpff"], cpff, ABS_THRESHOLDS["banking_cpff"]) if cpff is not None else None
    ccc_m = dynamic_metric(series["ccc_oas"], ccc_oas, ABS_THRESHOLDS["leveraged_ccc"]) if ccc_oas is not None else None

    rv_series = realized_yield_vol_series(series["dgs10"], 20)
    rv_d, rv = latest(rv_series)
    rv_m = dynamic_metric(rv_series, rv, ABS_THRESHOLDS["rates_liquidity"]) if rv is not None else None
    vix_m = dynamic_metric(series["vix"], vix, (20.0, 30.0, 40.0))
    move_manual = manual.get("move_index", {}).get("value")
    move_score = None if move_manual is None else absolute_anchor(float(move_manual), (90.0, 120.0, 160.0))
    rate_candidates = [x for x in [rv_m["score"] if rv_m else None, vix_m["score"] if vix_m else None, move_score] if x is not None]
    rates_score = max(rate_candidates) if rate_candidates else None
    rates_components = comp_or_empty(rv_m)
    if vix_m and (rates_score == vix_m["score"]):
        rates_components = vix_m["components"]

    eu_series = common_spread_series(series["italy10"], series["germany10"])
    eu_d, eu_auto = latest(eu_series)
    eu_override = manual.get("europe_daily_spread_bps", {}).get("value")
    europe_bps = float(eu_override) if eu_override is not None else eu_auto
    if eu_override is not None:
        eu_anchor = absolute_anchor(europe_bps, ABS_THRESHOLDS["europe"])
        eu_m = {"score": eu_anchor, "components": {"level": eu_anchor, "deviation": None, "velocity": None}, "stats": {}}
        eu_d = manual.get("europe_daily_spread_bps", {}).get("as_of")
    else:
        eu_m = dynamic_metric(eu_series, europe_bps, ABS_THRESHOLDS["europe"], short=1, medium=3, lookback=60) if europe_bps is not None else None

    oil_m = dynamic_metric(series["wti"], wti, ABS_THRESHOLDS["energy_oil"]) if wti is not None else None
    gas_m = dynamic_metric(series["gas"], gas, ABS_THRESHOLDS["energy_gas"]) if gas is not None else None
    energy_candidates = [x for x in [oil_m["score"] if oil_m else None, gas_m["score"] if gas_m else None] if x is not None]
    energy_score = max(energy_candidates) if energy_candidates else None
    energy_components = comp_or_empty(oil_m if oil_m and energy_score == oil_m["score"] else gas_m)

    dc_score, dc_meta = event_adjusted_score(manual["data_center_financing"], today)
    pc_event_score, pc_meta = event_adjusted_score(manual["private_credit"], today)
    bank_score, bank_meta = event_adjusted_score(manual["bank_ai_inventory"], today)

    def manual_number(key):
        value = manual.get(key, {}).get("value")
        return None if value is None else float(value)

    cdx_bps = manual_number("cdx_hy_spread_bps")
    clo_aaa_bps = manual_number("clo_aaa_spread_bps")
    clo_bbb_bps = manual_number("clo_bbb_spread_bps")
    bank_cds_bps = manual_number("bank_cds_bps")
    bdc_discount_pct = manual_number("bdc_discount_pct")

    cdx_score = absolute_anchor(cdx_bps, (350.0, 500.0, 800.0)) if cdx_bps is not None else None
    clo_aaa_score = absolute_anchor(clo_aaa_bps, (130.0, 200.0, 350.0)) if clo_aaa_bps is not None else None
    clo_bbb_score = absolute_anchor(clo_bbb_bps, (400.0, 700.0, 1200.0)) if clo_bbb_bps is not None else None
    bank_cds_score = absolute_anchor(bank_cds_bps, (100.0, 200.0, 400.0)) if bank_cds_bps is not None else None
    bdc_score = absolute_anchor(bdc_discount_pct, (5.0, 15.0, 30.0)) if bdc_discount_pct is not None else None

    leveraged_candidates = [x for x in [ccc_m["score"] if ccc_m else None, cdx_score, clo_aaa_score, clo_bbb_score] if x is not None]
    leveraged_score = max(leveraged_candidates) if leveraged_candidates else None
    leveraged_components = comp_or_empty(ccc_m)
    if leveraged_score in [x for x in [cdx_score, clo_aaa_score, clo_bbb_score] if x is not None]:
        leveraged_components = {"level": leveraged_score, "deviation": None, "velocity": None}

    banking_candidates = [x for x in [cpff_m["score"] if cpff_m else None, bank_cds_score] if x is not None]
    banking_score = max(banking_candidates) if banking_candidates else None
    banking_components = comp_or_empty(cpff_m)
    if bank_cds_score is not None and banking_score == bank_cds_score:
        banking_components = {"level": banking_score, "deviation": None, "velocity": None}

    pc_candidates = [x for x in [pc_event_score, bdc_score] if x is not None]
    pc_score = max(pc_candidates) if pc_candidates else None

    scores = {
        "ig_credit": None if ig_m is None else ig_m["score"],
        "hy_credit": None if hy_m is None else hy_m["score"],
        "leveraged_credit": None if leveraged_score is None else round(leveraged_score, 1),
        "financial_stress": None if fs_m is None else fs_m["score"],
        "rates_liquidity": None if rates_score is None else round(rates_score, 1),
        "funding_market": None if funding_m is None else funding_m["score"],
        "banking_stress": None if banking_score is None else round(banking_score, 1),
        "europe": None if eu_m is None else round(eu_m["score"], 1),
        "energy": None if energy_score is None else round(energy_score, 1),
        "data_center": dc_score,
        "private_credit": pc_score,
        "bank_ai": bank_score,
    }

    raw_score, coverage_weight = weighted_average(scores)
    coverage_pct = round(coverage_weight, 1)
    breadth = breadth_overlay(scores)
    bonus = synchronized_bonus(breadth)
    score = None if raw_score is None else round(clamp(raw_score + bonus), 1)

    market_keys = [
        "ig_credit", "hy_credit", "leveraged_credit", "financial_stress",
        "rates_liquidity", "funding_market", "banking_stress", "europe", "energy"
    ]
    market_scores = {k: scores.get(k) for k in market_keys}
    market_raw_score, market_covered_weight = weighted_average(market_scores)
    market_total_weight = sum(WEIGHTS[k] for k in market_keys)
    market_coverage_pct = round(100.0 * market_covered_weight / market_total_weight, 1) if market_total_weight else 0.0
    market_score = None if market_raw_score is None else round(clamp(market_raw_score + bonus), 1)
    lvl = score_level(score)
    stage, stage_label, stage_note = transmission_stage(scores, breadth)

    pillars = [
        {"name": "Broad Credit", "score": pillar_score(scores, ["ig_credit", "hy_credit", "leveraged_credit"])},
        {"name": "Funding / Liquidity", "score": pillar_score(scores, ["financial_stress", "rates_liquidity", "funding_market"])},
        {"name": "Banking", "score": pillar_score(scores, ["banking_stress", "bank_ai"])},
        {"name": "AI / Private Credit", "score": pillar_score(scores, ["data_center", "private_credit", "bank_ai"])},
        {"name": "Europe / Energy", "score": pillar_score(scores, ["europe", "energy"])},
    ]

    if coverage_pct < 70:
        summary = f"{lvl}: data coverage is only {coverage_pct:.0f}%; treat the composite as provisional."
    elif stage >= 3:
        summary = f"{lvl}: broad credit and funding/liquidity stress are synchronized. Cross-market contagion is visible."
    elif stage == 2:
        summary = f"{lvl}: stress has begun to propagate into broad corporate credit."
    elif stage == 1:
        summary = f"{lvl}: AI/private-credit stress remains mainly sectoral; broad credit contagion is not yet confirmed."
    else:
        summary = f"{lvl}: no material sector-to-system transmission signal."

    def indicator(id_, name, score_, value, source, mode, as_of, weight, url, note, components=None, stats=None, quality=None):
        return {
            "id": id_, "name": name, "score": score_, "value": value, "source": source, "mode": mode,
            "as_of": as_of, "weight": weight, "source_url": url, "note": note,
            "components": components or {"level": None, "deviation": None, "velocity": None},
            "stats": stats or {}, "quality": quality or {}
        }

    indicators = [
        indicator("ig_credit","US IG Corporate OAS",scores["ig_credit"],fmt(ig,"%"),"FRED BAMLC0A0CM","AUTO-DYNAMIC",ig_d,WEIGHTS["ig_credit"],
                  "https://fred.stlouisfed.org/series/BAMLC0A0CM",
                  "45% absolute level + 30% deviation from ~5y history + 25% 5/20-observation deterioration speed.",
                  comp_or_empty(ig_m), ig_m["stats"] if ig_m else None),
        indicator("hy_credit","US High Yield OAS",scores["hy_credit"],fmt(hy,"%"),"FRED BAMLH0A0HYM2","AUTO-DYNAMIC",hy_d,WEIGHTS["hy_credit"],
                  "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
                  "Core contagion channel. Fast widening can score high even before the absolute OAS reaches crisis thresholds.",
                  comp_or_empty(hy_m), hy_m["stats"] if hy_m else None),
        indicator("leveraged_credit","Leveraged / Structured Credit",scores["leveraged_credit"],
                  f"CCC OAS {fmt(ccc_oas,'%')}" + (f" / CDX HY {fmt(cdx_bps,' bp',0)}" if cdx_bps is not None else "") + (f" / CLO BBB {fmt(clo_bbb_bps,' bp',0)}" if clo_bbb_bps is not None else ""),
                  "FRED CCC OAS + optional CDX/CLO","AUTO/OVERRIDE",ccc_d,WEIGHTS["leveraged_credit"],
                  "https://fred.stlouisfed.org/series/BAMLH0A3HYC",
                  "CCC OAS is the automatic leveraged-credit proxy. Optional CDX HY and CLO AAA/BBB spreads can override when they show more stress.",
                  leveraged_components, {"ccc_oas":ccc_oas,"cdx_hy_bps":cdx_bps,"clo_aaa_bps":clo_aaa_bps,"clo_bbb_bps":clo_bbb_bps}),
        indicator("financial_stress","St. Louis Financial Stress",scores["financial_stress"],fmt(stlfsi,"",2),"FRED STLFSI4","AUTO-DYNAMIC",fs_d,WEIGHTS["financial_stress"],
                  "https://fred.stlouisfed.org/series/STLFSI4",
                  "Cross-market stress measured against both fixed anchors and its own recent distribution.",
                  comp_or_empty(fs_m), fs_m["stats"] if fs_m else None),
        indicator("rates_liquidity","Treasury Vol / Liquidity",scores["rates_liquidity"],
                  f"RV20 {fmt(rv,' bp')} / VIX {fmt(vix)}" + (f" / MOVE {fmt(float(move_manual))}" if move_manual is not None else ""),
                  "FRED DGS10 + VIXCLS","AUTO/HYBRID",rv_d or d10_d,WEIGHTS["rates_liquidity"],
                  "https://fred.stlouisfed.org/series/DGS10",
                  "Uses the strongest signal from 10Y realized yield volatility, VIX, and optional MOVE. Missing inputs are not treated as zero.",
                  rates_components, {"rv": rv, "move": move_manual, "vix": vix}),
        indicator("funding_market","Repo / Funding Market",scores["funding_market"],fmt(sofr_iorb_bps," bp",1),
                  "FRED SOFR - IORB","AUTO-DYNAMIC",sofr_iorb_d,WEIGHTS["funding_market"],
                  "https://fred.stlouisfed.org/graph/?id=SOFR,IORB",
                  "Positive SOFR-IORB pressure is monitored against absolute thresholds, its own distribution and deterioration velocity.",
                  comp_or_empty(funding_m), funding_m["stats"] if funding_m else None),
        indicator("banking_stress","Bank Short-term Funding",scores["banking_stress"],
                  f"CP-FF {fmt(cpff,'%')}" + (f" / Bank CDS {fmt(bank_cds_bps,' bp',0)}" if bank_cds_bps is not None else ""),
                  "FRED CPFF + optional bank CDS","AUTO/OVERRIDE",cpff_d,WEIGHTS["banking_stress"],
                  "https://fred.stlouisfed.org/series/CPFF",
                  "Financial commercial-paper spread is the public banking-funding proxy; an entered bank CDS reading overrides if more stressed.",
                  banking_components, {"cpff":cpff,"bank_cds_bps":bank_cds_bps}),
        indicator("europe","Italy-Bund 10Y Spread",scores["europe"],fmt(europe_bps," bp",0),
                  "OECD via FRED" if eu_override is None else "Manual daily override",
                  "AUTO-DYNAMIC" if eu_override is None else "HYBRID",eu_d,WEIGHTS["europe"],
                  "https://fred.stlouisfed.org/graph/?g=j3d3",
                  "Monthly automatic series uses level/deviation/velocity. A daily manual override uses the absolute anchor only.",
                  comp_or_empty(eu_m), eu_m["stats"] if eu_m else None),
        indicator("energy","Energy Shock",scores["energy"],f"WTI ${fmt(wti,'',2)} / Henry Hub ${fmt(gas,'',2)}",
                  "FRED DCOILWTICO + DHHNGSP","AUTO-DYNAMIC",max([x for x in [wti_d,gas_d] if x] or [None]),WEIGHTS["energy"],
                  "https://fred.stlouisfed.org/series/DCOILWTICO",
                  "Uses the more stressed oil/gas signal; fast shocks matter even before absolute prices reach extreme thresholds.",
                  energy_components, {"oil_score": oil_m["score"] if oil_m else None, "gas_score": gas_m["score"] if gas_m else None}),
        indicator("data_center","AI Data-center Financing",scores["data_center"],"Event score","Reuters / deal evidence","EVENT-DECAY",manual["data_center_financing"].get("as_of"),WEIGHTS["data_center"],
                  manual["data_center_financing"].get("source_url"),manual["data_center_financing"]["note"],
                  {"level": scores["data_center"], "deviation": None, "velocity": None}, dc_meta, {"confidence": manual["data_center_financing"].get("confidence")}),
        indicator("private_credit","Private-credit Liquidity",scores["private_credit"],
                  "Event score" + (f" / BDC disc {fmt(bdc_discount_pct,'%',1)}" if bdc_discount_pct is not None else ""),
                  "Fund disclosures / optional BDC NAV discount","EVENT/MARKET",manual["private_credit"].get("as_of"),WEIGHTS["private_credit"],
                  manual["private_credit"].get("source_url"),manual["private_credit"]["note"],
                  {"level": scores["private_credit"], "deviation": None, "velocity": None},
                  dict(pc_meta, bdc_discount_pct=bdc_discount_pct, bdc_score=bdc_score),
                  {"confidence": manual["private_credit"].get("confidence")}),
        indicator("bank_ai","Bank AI-credit Inventory",scores["bank_ai"],"Event score","Syndication / lender evidence","EVENT-DECAY",manual["bank_ai_inventory"].get("as_of"),WEIGHTS["bank_ai"],
                  manual["bank_ai_inventory"].get("source_url"),manual["bank_ai_inventory"]["note"],
                  {"level": scores["bank_ai"], "deviation": None, "velocity": None}, bank_meta, {"confidence": manual["bank_ai_inventory"].get("confidence")}),
    ]

    flags = []
    if breadth["score"] is not None and breadth["score"] >= 50:
        flags.append({"type":"BREADTH","label":f"Cross-market breadth {breadth['score']:.0f}%"})
    if bonus > 0:
        flags.append({"type":"SYNC","label":f"Synchronized-stress overlay +{bonus:.1f}"})
    if (pillar_score(scores, ["data_center","private_credit","bank_ai"]) or 0) >= 45:
        flags.append({"type":"AI_CREDIT","label":"AI / Private Credit stress is material"})
    if (pillar_score(scores, ["funding_market","banking_stress","financial_stress"]) or 0) >= 45:
        flags.append({"type":"FUNDING","label":"Funding / bank stress is material"})
    if (scores.get("leveraged_credit") or 0) >= 55:
        flags.append({"type":"LEVERAGED","label":"Leveraged / structured credit stress is elevated"})
    if coverage_pct < 80:
        flags.append({"type":"DATA","label":f"Data coverage {coverage_pct:.0f}%"})
    if not flags:
        flags.append({"type":"CLEAR","label":"No cross-market contagion trigger"})

    curve = None if dgs10 is None or dgs2 is None else (dgs10 - dgs2) * 100.0
    payload = {
        "version": 5,
        "updated_at": now.isoformat().replace("+00:00","Z"),
        "score": score,
        "raw_score": raw_score,
        "market_score": market_score,
        "market_raw_score": market_raw_score,
        "market_coverage_pct": market_coverage_pct,
        "synchronization_bonus": bonus,
        "level": lvl,
        "summary": summary,
        "coverage_pct": coverage_pct,
        "breadth": breadth,
        "transmission": {"stage":stage,"label":stage_label,"note":stage_note},
        "flags": flags,
        "pillars": pillars,
        "weights": WEIGHTS,
        "methodology": {
            "auto_components": {"level_weight":45,"deviation_weight":30,"velocity_weight":25},
            "lookback_observations": LOOKBACK,
            "missing_data_policy": "exclude_and_renormalize",
            "event_decay": "confidence multiplier plus age-based decay after 30 days",
            "v4_layers": "SOFR-IORB funding, financial CP spread, CCC OAS, optional CDX/CLO/bank-CDS/BDC overrides",
            "v5_validation": "walk-forward historical backtest uses market-only score; no future observations are allowed"
        },
        "diagnostics": {
            "us10y": dgs10, "us2y": dgs2, "curve_2s10s_bps": curve, "vix": vix,
            "realized_10y_vol_bps": rv, "move_manual": move_manual,
            "italy_bund_bps": europe_bps, "wti": wti, "gas": gas,
            "sofr": sofr, "iorb": iorb, "sofr_iorb_bps": sofr_iorb_bps,
            "cpff": cpff, "ccc_oas": ccc_oas,
            "cdx_hy_bps": cdx_bps, "clo_aaa_bps": clo_aaa_bps, "clo_bbb_bps": clo_bbb_bps,
            "bank_cds_bps": bank_cds_bps, "bdc_discount_pct": bdc_discount_pct
        },
        "data_failures": failures,
        "indicators": indicators
    }

    OUTPUT.write_text("window.__RISK_DATA__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")

    history = load_history()
    save_history(history, {
        "date": now.date().isoformat(), "score": score, "raw_score": raw_score, "market_score": market_score,
        "level": lvl, "stage": stage, "coverage_pct": coverage_pct, "market_coverage_pct": market_coverage_pct,
        "breadth": breadth["score"], "synchronization_bonus": bonus,
        "pillars": {x["name"]: x["score"] for x in pillars},
        "hy_oas": hy, "ig_oas": ig, "ccc_oas": ccc_oas, "stlfsi": stlfsi, "rates_vol": rv,
        "sofr_iorb_bps": sofr_iorb_bps, "cpff": cpff,
        "italy_bund_bps": europe_bps, "wti": wti
    })

    print(json.dumps({
        "version":5,"score":score,"market_score":market_score,"raw_score":raw_score,"level":lvl,"stage":stage,
        "coverage_pct":coverage_pct,"breadth":breadth,"bonus":bonus,"failures":failures
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
