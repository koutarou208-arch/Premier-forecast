#!/usr/bin/env python3
import bisect
import json
import pathlib
import re
from datetime import date, timedelta

import update_data as core

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "data" / "backtest_config.json"
OUT_JSON = ROOT / "data" / "backtest.json"
OUT_JS = ROOT / "data" / "backtest.js"
LATEST_JS = ROOT / "data" / "latest.js"

MARKET_KEYS = [
    "ig_credit", "hy_credit", "leveraged_credit", "financial_stress",
    "rates_liquidity", "funding_market", "banking_stress", "europe", "energy"
]
MARKET_WEIGHT = sum(core.WEIGHTS[k] for k in MARKET_KEYS)

def parse_day(s):
    return date.fromisoformat(s)

def build_index(series):
    return [d for d, _ in series]

def cut(series, dates, day):
    i = bisect.bisect_right(dates, day) 
    return series[:i]

def latest_cut(series, dates, day):
    i = bisect.bisect_right(dates, day)
    return series[i-1] if i else (None, None)

def max_signal(metric_list):
    vals = [x for x in metric_list if x is not None]
    return max(vals) if vals else None

def weighted_market_score(scores):
    raw, den = core.weighted_average({k: scores.get(k) for k in MARKET_KEYS})
    coverage = round(100.0 * den / MARKET_WEIGHT, 1) if MARKET_WEIGHT else 0.0
    breadth = core.breadth_overlay(scores)
    bonus = core.synchronized_bonus(breadth)
    score = None if raw is None else round(core.clamp(raw + bonus), 1)
    stage, label, _ = core.transmission_stage(scores, breadth)
    return score, raw, coverage, breadth, bonus, stage, label

def percentile(sample, x):
    if x is None or not sample:
        return None
    return round(100.0 * sum(v <= x for v in sample) / len(sample), 1)

def quantile(sample, q):
    if not sample:
        return None
    s = sorted(sample)
    pos = (len(s) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return round(s[lo] * (1-frac) + s[hi] * frac, 1)

def in_window(day, w):
    return parse_day(w["start"]) <= day <= parse_day(w["end"])

def first_cross(rows, field, threshold, start_day, end_day):
    for r in rows:
        d = parse_day(r["date"])
        if start_day <= d <= end_day and r.get(field) is not None and r[field] >= threshold:
            return r["date"]
    return None

def first_stage(rows, threshold, start_day, end_day):
    for r in rows:
        d = parse_day(r["date"])
        if start_day <= d <= end_day and r.get("stage", 0) >= threshold:
            return r["date"]
    return None

def lead_days(first_date, reference):
    if not first_date:
        return None
    return (parse_day(reference) - parse_day(first_date)).days

def read_latest():
    if not LATEST_JS.exists():
        return {}
    text = LATEST_JS.read_text(encoding="utf-8")
    m = re.search(r"window.__RISK_DATA__\s*=\s*(\{.*\});\s*$", text, re.S)
    return json.loads(m.group(1)) if m else {}

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    failures = []
    series = core.fetch_all_series(failures, start_date="1990-01-01")

    # Historical-only funding proxy for periods before SOFR/IORB history.
    try:
        ted = core.fetch_series("TEDRATE", start_date="1990-01-01")
    except Exception as e:
        ted = []
        failures.append(f"TEDRATE: {e}")

    rv = core.realized_yield_vol_series(series["dgs10"], 20)
    eu = core.common_spread_series(series["italy10"], series["germany10"])
    sofr_iorb = core.common_spread_series(series["sofr"], series["iorb"])

    indices = {k: build_index(v) for k, v in series.items()}
    rv_dates = build_index(rv)
    eu_dates = build_index(eu)
    funding_dates = build_index(sofr_iorb)
    ted_dates = build_index(ted)

    anchor = [(d, v) for d, v in series["ig_oas"] if d >= cfg["start_date"]]
    sample_dates = [d for i, (d, _) in enumerate(anchor) if i % 5 == 0]
    if anchor and anchor[-1][0] not in sample_dates:
        sample_dates.append(anchor[-1][0])

    rows = []
    for day in sample_dates:
        # Credit
        ig_s = cut(series["ig_oas"], indices["ig_oas"], day)
        hy_s = cut(series["hy_oas"], indices["hy_oas"], day)
        ccc_s = cut(series["ccc_oas"], indices["ccc_oas"], day)
        fs_s = cut(series["stlfsi"], indices["stlfsi"], day)
        vix_s = cut(series["vix"], indices["vix"], day)
        wti_s = cut(series["wti"], indices["wti"], day)
        gas_s = cut(series["gas"], indices["gas"], day)
        cpff_s = cut(series["cpff"], indices["cpff"], day)
        rv_s = cut(rv, rv_dates, day)
        eu_s = cut(eu, eu_dates, day)
        funding_s = cut(sofr_iorb, funding_dates, day)
        ted_s = cut(ted, ted_dates, day)

        _, ig = core.latest(ig_s)
        _, hy = core.latest(hy_s)
        _, ccc = core.latest(ccc_s)
        _, fs = core.latest(fs_s)
        _, vix = core.latest(vix_s)
        _, wti = core.latest(wti_s)
        _, gas = core.latest(gas_s)
        _, cpff = core.latest(cpff_s)
        _, rv_now = core.latest(rv_s)
        _, eu_now = core.latest(eu_s)
        _, funding_now = core.latest(funding_s)
        _, ted_now = core.latest(ted_s)

        ig_m = core.dynamic_metric(ig_s, ig, core.ABS_THRESHOLDS["ig_credit"]) if ig is not None else None
        hy_m = core.dynamic_metric(hy_s, hy, core.ABS_THRESHOLDS["hy_credit"]) if hy is not None else None
        ccc_m = core.dynamic_metric(ccc_s, ccc, core.ABS_THRESHOLDS["leveraged_ccc"]) if ccc is not None else None
        fs_m = core.dynamic_metric(fs_s, fs, core.ABS_THRESHOLDS["financial_stress"]) if fs is not None else None
        rv_m = core.dynamic_metric(rv_s, rv_now, core.ABS_THRESHOLDS["rates_liquidity"]) if rv_now is not None else None
        vix_m = core.dynamic_metric(vix_s, vix, (20.0, 30.0, 40.0)) if vix is not None else None
        cpff_m = core.dynamic_metric(cpff_s, cpff, core.ABS_THRESHOLDS["banking_cpff"]) if cpff is not None else None
        eu_m = core.dynamic_metric(eu_s, eu_now, core.ABS_THRESHOLDS["europe"], short=1, medium=3) if eu_now is not None else None
        oil_m = core.dynamic_metric(wti_s, wti, core.ABS_THRESHOLDS["energy_oil"]) if wti is not None else None
        gas_m = core.dynamic_metric(gas_s, gas, core.ABS_THRESHOLDS["energy_gas"]) if gas is not None else None

        # Production funding proxy where history exists. Before that, use TED only for backtest comparability.
        funding_source = "SOFR-IORB"
        if funding_now is not None:
            funding_m = core.dynamic_metric(funding_s, funding_now, core.ABS_THRESHOLDS["funding_market"])
        elif ted_now is not None:
            funding_source = "TED legacy"
            funding_m = core.dynamic_metric(ted_s, ted_now, (0.40, 1.00, 2.00))
        else:
            funding_source = "missing"
            funding_m = None

        rates_score = max_signal([rv_m["score"] if rv_m else None, vix_m["score"] if vix_m else None])
        energy_score = max_signal([oil_m["score"] if oil_m else None, gas_m["score"] if gas_m else None])

        scores = {
            "ig_credit": ig_m["score"] if ig_m else None,
            "hy_credit": hy_m["score"] if hy_m else None,
            "leveraged_credit": ccc_m["score"] if ccc_m else None,
            "financial_stress": fs_m["score"] if fs_m else None,
            "rates_liquidity": rates_score,
            "funding_market": funding_m["score"] if funding_m else None,
            "banking_stress": cpff_m["score"] if cpff_m else None,
            "europe": eu_m["score"] if eu_m else None,
            "energy": energy_score,
            "data_center": None,
            "private_credit": None,
            "bank_ai": None,
        }
        score, raw, coverage, breadth, bonus, stage, stage_label = weighted_market_score(scores)
        rows.append({
            "date": day,
            "score": score,
            "raw_score": raw,
            "coverage_pct": coverage,
            "breadth": breadth["score"],
            "stage": stage,
            "stage_label": stage_label,
            "funding_source": funding_source,
            "channels": {k: scores[k] for k in MARKET_KEYS},
        })

    windows = cfg["windows"]
    events = []
    pre_days = int(cfg.get("pre_reference_days", 120))
    for w in windows:
        start = parse_day(w["start"])
        end = parse_day(w["end"])
        ref = parse_day(w["reference_date"])
        eval_start = min(start, ref - timedelta(days=pre_days))
        segment = [r for r in rows if eval_start <= parse_day(r["date"]) <= end]
        crisis_segment = [r for r in rows if start <= parse_day(r["date"]) <= end]
        if not crisis_segment:
            continue
        peak = max((r for r in crisis_segment if r["score"] is not None), key=lambda r: r["score"], default=None)
        first25 = first_cross(rows, "score", 25, eval_start, end)
        first45 = first_cross(rows, "score", 45, eval_start, end)
        first65 = first_cross(rows, "score", 65, eval_start, end)
        st2 = first_stage(rows, 2, eval_start, end)
        events.append({
            **w,
            "observations": len(crisis_segment),
            "max_score": None if peak is None else peak["score"],
            "max_score_date": None if peak is None else peak["date"],
            "max_stage": max((r["stage"] for r in crisis_segment), default=None),
            "first_watch": first25,
            "first_elevated": first45,
            "first_high": first65,
            "first_stage2": st2,
            "lead_days_watch_vs_reference": lead_days(first25, w["reference_date"]),
            "lead_days_elevated_vs_reference": lead_days(first45, w["reference_date"]),
            "lead_days_high_vs_reference": lead_days(first65, w["reference_date"]),
            "lead_days_stage2_vs_reference": lead_days(st2, w["reference_date"]),
        })

    def labeled(d):
        return any(in_window(d, w) for w in windows)

    outside = [r["score"] for r in rows if r["score"] is not None and not labeled(parse_day(r["date"]))]
    all_scores = [r["score"] for r in rows if r["score"] is not None]
    crisis_rows = [r for r in rows if r["score"] is not None and labeled(parse_day(r["date"]))]

    thresholds = [25, 45, 65, 80]
    outside_rates = {
        str(t): round(100.0 * sum(v >= t for v in outside) / len(outside), 2) if outside else None
        for t in thresholds
    }
    crisis_rates = {
        str(t): round(100.0 * sum(r["score"] >= t for r in crisis_rows) / len(crisis_rows), 2) if crisis_rows else None
        for t in thresholds
    }

    current = read_latest()
    current_market = current.get("market_score")
    result = {
        "version": 5,
        "method": {
            "lookahead": False,
            "sampling": cfg["sampling"],
            "market_only": True,
            "historical_funding_fallback": "TEDRATE only when SOFR-IORB is unavailable",
            "manual_event_channels_in_backtest": False,
            "weights": {k: core.WEIGHTS[k] for k in MARKET_KEYS},
        },
        "range": {
            "start": rows[0]["date"] if rows else None,
            "end": rows[-1]["date"] if rows else None,
            "observations": len(rows),
        },
        "current": {
            "market_score": current_market,
            "percentile_all_history": percentile(all_scores, current_market),
            "percentile_outside_labeled_windows": percentile(outside, current_market),
        },
        "distribution": {
            "outside_windows_p90": quantile(outside, 0.90),
            "outside_windows_p95": quantile(outside, 0.95),
            "outside_windows_p99": quantile(outside, 0.99),
            "all_history_p95": quantile(all_scores, 0.95),
        },
        "alert_audit": {
            "outside_labeled_windows_rate_pct": outside_rates,
            "inside_labeled_windows_rate_pct": crisis_rates,
            "note": "Outside-window alerts are not automatically false positives; unlabeled stress episodes may exist."
        },
        "events": events,
        "failures": failures,
        "series": rows,
    }
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_JS.write_text("window.__BACKTEST_DATA__ = " + json.dumps(result, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")

    print(json.dumps({
        "version": 5,
        "observations": len(rows),
        "current_market_score": current_market,
        "current_percentile": result["current"]["percentile_outside_labeled_windows"],
        "outside_elevated_rate_pct": outside_rates["45"],
        "events": [{"id": e["id"], "max": e["max_score"], "stage": e["max_stage"]} for e in events],
        "failures": failures,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
