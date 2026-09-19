#!/usr/bin/env python3
import bisect
import json
import pathlib
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
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

# ICE BofA series on FRED are limited to a rolling three-year window from April 2026.
# Historical validation therefore uses long-history public proxies for the three credit channels.
PROXY_SERIES = {
    "baa10y": "BAA10Y",
    "nfci_credit": "NFCICREDIT",
    "nfci_risk": "NFCIRISK",
    "stlfsi": "STLFSI4",
    "vix": "VIXCLS",
    "wti": "DCOILWTICO",
    "gas": "DHHNGSP",
    "dgs10": "DGS10",
    "italy10": "IRLTLT01ITM156N",
    "germany10": "IRLTLT01DEM156N",
    "sofr": "SOFR",
    "iorb": "IORB",
    "cpff": "CPFF",
    "ted": "TEDRATE",
}

def parse_day(s):
    return date.fromisoformat(s)

def build_index(series):
    return [d for d, _ in series]

def cut(series, dates, day):
    i = bisect.bisect_right(dates, day)
    return series[:i]

def max_signal(values):
    vals = [x for x in values if x is not None]
    return max(vals) if vals else None

def fetch_proxies(failures, start_date="1990-01-01", max_workers=3):
    out = {k: [] for k in PROXY_SERIES}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {
            ex.submit(core.fetch_series, sid, start_date): name
            for name, sid in PROXY_SERIES.items()
        }
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                out[name] = fut.result()
            except Exception as e:
                failures.append(f"{name}: {e}")
    return out

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
    f = pos - lo
    return round(s[lo] * (1-f) + s[hi] * f, 1)

def in_window(day, w):
    return parse_day(w["start"]) <= day <= parse_day(w["end"])

def first_cross(rows, field, threshold, start_day, end_day):
    for row in rows:
        d = parse_day(row["date"])
        if start_day <= d <= end_day and row.get(field) is not None and row[field] >= threshold:
            return row["date"]
    return None

def first_stage(rows, threshold, start_day, end_day):
    for row in rows:
        d = parse_day(row["date"])
        if start_day <= d <= end_day and row.get("stage", 0) >= threshold:
            return row["date"]
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

def metric(series, threshold, frequency="daily"):
    if not series:
        return None
    _, value = core.latest(series)
    if value is None:
        return None
    if frequency == "weekly":
        return core.dynamic_metric(series, value, threshold, short=4, medium=13, lookback=260)
    if frequency == "monthly":
        return core.dynamic_metric(series, value, threshold, short=1, medium=3, lookback=60)
    return core.dynamic_metric(series, value, threshold, short=5, medium=20, lookback=1260)

def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    failures = []
    series = fetch_proxies(failures)
    indices = {k: build_index(v) for k, v in series.items()}

    rv_full = core.realized_yield_vol_series(series["dgs10"], 20)
    eu_full = core.common_spread_series(series["italy10"], series["germany10"])
    funding_full = core.common_spread_series(series["sofr"], series["iorb"])
    rv_dates = build_index(rv_full)
    eu_dates = build_index(eu_full)
    funding_dates = build_index(funding_full)

    # Weekly NFCI risk series is the stable historical anchor.
    # Add daily Treasury dates around labeled episodes so short funding shocks are not lost.
    anchor = [(d, v) for d, v in series["nfci_risk"] if d >= cfg["start_date"]]
    sample_set = {d for d, _ in anchor}
    pre_days = int(cfg.get("pre_reference_days", 120))
    for w in cfg["windows"]:
        start = min(parse_day(w["start"]), parse_day(w["reference_date"]) - timedelta(days=pre_days))
        end = parse_day(w["end"])
        for d, _ in series["dgs10"]:
            dd = parse_day(d)
            if start <= dd <= end:
                sample_set.add(d)
    sample_dates = sorted(sample_set)

    rows = []
    for day in sample_dates:
        baa_s = cut(series["baa10y"], indices["baa10y"], day)
        credit_s = cut(series["nfci_credit"], indices["nfci_credit"], day)
        risk_s = cut(series["nfci_risk"], indices["nfci_risk"], day)
        fs_s = cut(series["stlfsi"], indices["stlfsi"], day)
        vix_s = cut(series["vix"], indices["vix"], day)
        wti_s = cut(series["wti"], indices["wti"], day)
        gas_s = cut(series["gas"], indices["gas"], day)
        cpff_s = cut(series["cpff"], indices["cpff"], day)
        ted_s = cut(series["ted"], indices["ted"], day)
        rv_s = cut(rv_full, rv_dates, day)
        eu_s = cut(eu_full, eu_dates, day)
        funding_s = cut(funding_full, funding_dates, day)

        baa_m = metric(baa_s, (2.50, 4.00, 6.00), "daily")
        credit_m = metric(credit_s, (0.00, 0.75, 1.50), "weekly")
        risk_m = metric(risk_s, (0.00, 1.00, 2.00), "weekly")
        fs_m = metric(fs_s, core.ABS_THRESHOLDS["financial_stress"], "weekly")
        rv_m = metric(rv_s, core.ABS_THRESHOLDS["rates_liquidity"], "daily")
        vix_m = metric(vix_s, (20.0, 30.0, 40.0), "daily")
        cpff_m = metric(cpff_s, core.ABS_THRESHOLDS["banking_cpff"], "daily")
        eu_m = metric(eu_s, core.ABS_THRESHOLDS["europe"], "monthly")
        oil_m = metric(wti_s, core.ABS_THRESHOLDS["energy_oil"], "daily")
        gas_m = metric(gas_s, core.ABS_THRESHOLDS["energy_gas"], "daily")

        _, funding_now = core.latest(funding_s)
        _, ted_now = core.latest(ted_s)
        if funding_now is not None:
            funding_m = metric(funding_s, core.ABS_THRESHOLDS["funding_market"], "daily")
            funding_source = "SOFR-IORB"
        elif ted_now is not None:
            funding_m = metric(ted_s, (0.40, 1.00, 2.00), "daily")
            funding_source = "TED legacy"
        else:
            funding_m = None
            funding_source = "missing"

        rates_score = max_signal([
            rv_m["score"] if rv_m else None,
            vix_m["score"] if vix_m else None,
        ])
        energy_score = max_signal([
            oil_m["score"] if oil_m else None,
            gas_m["score"] if gas_m else None,
        ])

        scores = {
            "ig_credit": baa_m["score"] if baa_m else None,
            "hy_credit": credit_m["score"] if credit_m else None,
            "leveraged_credit": risk_m["score"] if risk_m else None,
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
        crisis_segment = [x for x in rows if start <= parse_day(x["date"]) <= end]
        if not crisis_segment:
            continue
        peak = max((x for x in crisis_segment if x["score"] is not None), key=lambda x: x["score"], default=None)
        first25 = first_cross(rows, "score", 25, eval_start, end)
        first45 = first_cross(rows, "score", 45, eval_start, end)
        first65 = first_cross(rows, "score", 65, eval_start, end)
        st2 = first_stage(rows, 2, eval_start, end)
        events.append({
            **w,
            "observations": len(crisis_segment),
            "max_score": None if peak is None else peak["score"],
            "max_score_date": None if peak is None else peak["date"],
            "max_stage": max((x["stage"] for x in crisis_segment), default=None),
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

    outside = [x["score"] for x in rows if x["score"] is not None and not labeled(parse_day(x["date"]))]
    all_scores = [x["score"] for x in rows if x["score"] is not None]
    crisis_rows = [x for x in rows if x["score"] is not None and labeled(parse_day(x["date"]))]

    thresholds = [25, 45, 65, 80]
    outside_rates = {
        str(t): round(100.0 * sum(v >= t for v in outside) / len(outside), 2) if outside else None
        for t in thresholds
    }
    crisis_rates = {
        str(t): round(100.0 * sum(x["score"] >= t for x in crisis_rows) / len(crisis_rows), 2) if crisis_rows else None
        for t in thresholds
    }

    latest = read_latest()
    comparable_now = rows[-1]["score"] if rows else None
    result = {
        "version": 5,
        "method": {
            "lookahead": False,
            "sampling": cfg["sampling"],
            "market_only": True,
            "exact_production_replication": False,
            "surrogate_reason": "ICE BofA FRED series are restricted to a rolling 3-year history from April 2026.",
            "credit_proxies": {
                "ig_credit": "BAA10Y",
                "hy_credit": "NFCICREDIT",
                "leveraged_credit": "NFCIRISK"
            },
            "historical_funding_fallback": "TEDRATE before SOFR-IORB history",
            "manual_event_channels_in_backtest": False,
            "weights": {k: core.WEIGHTS[k] for k in MARKET_KEYS},
        },
        "range": {
            "start": rows[0]["date"] if rows else None,
            "end": rows[-1]["date"] if rows else None,
            "observations": len(rows),
        },
        "current": {
            "production_market_score": latest.get("market_score"),
            "historical_comparable_score": comparable_now,
            "percentile_all_history": percentile(all_scores, comparable_now),
            "percentile_outside_labeled_windows": percentile(outside, comparable_now),
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
        "historical_comparable_score": comparable_now,
        "current_percentile": result["current"]["percentile_outside_labeled_windows"],
        "outside_elevated_rate_pct": outside_rates["45"],
        "events": [{"id": e["id"], "max": e["max_score"], "stage": e["max_stage"]} for e in events],
        "failures": failures,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
