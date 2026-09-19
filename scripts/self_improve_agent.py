#!/usr/bin/env python3
"""Guardrailed self-improvement agent for Global Financial Crisis Watch.

Cycle:
1. Observe incumbent model/backtest/NN artifacts.
2. Generate small configuration candidates.
3. Evaluate candidates only on pre-2023 calibration data.
4. Apply strict regression/false-positive/event guardrails.
5. Accept at most one small configuration change.
6. Report holdout metrics separately; never use them for candidate selection.

The agent never rewrites Python code, labels, or validation windows.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CONFIG_PATH = DATA / "model_config.json"
POLICY_PATH = DATA / "agent_policy.json"
BACKTEST_PATH = DATA / "backtest.json"
NN_PATH = DATA / "nn_model.json"
WINDOWS_PATH = DATA / "backtest_config.json"
STATE_JSON = DATA / "agent_state.json"
STATE_JS = DATA / "agent_state.js"
HISTORY_PATH = DATA / "agent_history.json"

MARKET_KEYS = [
    "ig_credit", "hy_credit", "leveraged_credit", "financial_stress",
    "rates_liquidity", "funding_market", "banking_stress", "europe", "energy"
]
NN_BASE_FEATURES = MARKET_KEYS + ["breadth", "raw_score", "coverage_pct"]
NN_FEATURES = NN_BASE_FEATURES + [f"missing_{x}" for x in MARKET_KEYS]

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def parse_day(s):
    return date.fromisoformat(s)

def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))

def label_day(day, windows, lead_days):
    for w in windows:
        start = parse_day(w["start"]) - timedelta(days=lead_days)
        end = parse_day(w["end"])
        if start <= day <= end:
            return 1
    return 0

def sigmoid(x):
    x = np.clip(x, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-x))

def load_models(nn):
    out = []
    for raw in nn.get("models", []):
        out.append({k: np.asarray(v, dtype=np.float64) for k, v in raw.items()})
    return out

def nn_features(row):
    channels = row.get("channels", {})
    vals, missing = [], []
    for key in MARKET_KEYS:
        value = channels.get(key)
        missing.append(1.0 if value is None else 0.0)
        vals.append(0.0 if value is None else clamp(float(value))/100.0)
    vals.extend([
        0.0 if row.get("breadth") is None else clamp(float(row["breadth"]))/100.0,
        0.0 if row.get("raw_score") is None else clamp(float(row["raw_score"]))/100.0,
        0.0 if row.get("coverage_pct") is None else clamp(float(row["coverage_pct"]))/100.0,
    ])
    vals.extend(missing)
    return np.asarray(vals, dtype=np.float64)

def forward(model, X):
    a1 = np.tanh(X @ model["w1"] + model["b1"])
    a2 = np.tanh(a1 @ model["w2"] + model["b2"])
    return sigmoid(a2 @ model["w3"] + model["b3"]).reshape(-1)

def ensemble_predict(models, X):
    if not models:
        return np.zeros(len(X), dtype=np.float64)
    preds = np.stack([forward(m, X) for m in models], axis=0)
    return preds.mean(axis=0)

def weighted_rule(row, weights):
    channels = row.get("channels", {})
    num = den = 0.0
    for key in MARKET_KEYS:
        value = channels.get(key)
        if value is None:
            continue
        w = float(weights[key])
        num += float(value) * w
        den += w
    raw = num / den if den else 0.0

    available = [float(channels[k]) for k in MARKET_KEYS if channels.get(k) is not None]
    stressed = sum(v >= 45 for v in available)
    severe = sum(v >= 65 for v in available)
    bonus = 0.0
    if len(available) >= 6:
        if severe >= 6:
            bonus = 8.0
        elif stressed >= 6:
            bonus = 5.0
        elif stressed >= 4:
            bonus = 2.5
    return clamp(raw + bonus)

def roc_auc(y, p):
    pos = [v for v,t in zip(p,y) if t == 1]
    neg = [v for v,t in zip(p,y) if t == 0]
    if not pos or not neg:
        return None
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b: wins += 1
            elif a == b: ties += 1
    return (wins + 0.5*ties) / (len(pos)*len(neg))

def average_precision(y, p):
    order = np.argsort(-p)
    yy = y[order]
    total = int(np.sum(yy))
    if total == 0:
        return None
    tp = 0
    acc = 0.0
    for rank, label in enumerate(yy, start=1):
        if label == 1:
            tp += 1
            acc += tp / rank
    return acc / total

def choose_threshold(y, score):
    best = None
    for t in np.linspace(20.0, 80.0, 121):
        pred = score >= t
        pos = y == 1
        neg = ~pos
        tp = int(np.sum(pred & pos)); fn = int(np.sum((~pred) & pos))
        fp = int(np.sum(pred & neg)); tn = int(np.sum((~pred) & neg))
        tpr = tp/(tp+fn) if tp+fn else 0.0
        fpr = fp/(fp+tn) if fp+tn else 0.0
        bal = 0.5*(tpr + (1-fpr))
        precision = tp/(tp+fp) if tp+fp else 0.0
        candidate = {
            "threshold": float(t), "recall": tpr, "fpr": fpr,
            "specificity": 1-fpr, "precision": precision,
            "balanced_accuracy": bal
        }
        if best is None or (bal, -fpr) > (best["balanced_accuracy"], -best["fpr"]):
            best = candidate
    return best

def event_peaks(rows, scores, windows):
    out = {}
    for w in windows:
        if w.get("group") == "holdout":
            continue
        start, end = parse_day(w["start"]), parse_day(w["end"])
        vals = [float(s) for r,s in zip(rows,scores) if start <= parse_day(r["date"]) <= end]
        out[w["id"]] = max(vals) if vals else None
    return out

def event_recall(peaks, threshold):
    vals = [v for v in peaks.values() if v is not None]
    if not vals:
        return 0.0
    return sum(v >= threshold for v in vals)/len(vals)

def evaluate(rows, y, nn_pred, windows, weights, nn_weight, objective_weights):
    rule = np.asarray([weighted_rule(r, weights) for r in rows], dtype=np.float64)
    hybrid = (1.0-nn_weight)*rule + nn_weight*(nn_pred*100.0)
    auc = roc_auc(y, hybrid) or 0.0
    ap = average_precision(y, hybrid) or 0.0
    threshold = choose_threshold(y, hybrid)
    peaks = event_peaks(rows, hybrid, windows)
    ev_recall = event_recall(peaks, threshold["threshold"])
    objective = (
        objective_weights["roc_auc"] * auc +
        objective_weights["average_precision"] * ap +
        objective_weights["event_recall"] * ev_recall +
        objective_weights["specificity"] * threshold["specificity"]
    )
    return {
        "objective": float(objective),
        "roc_auc": float(auc),
        "average_precision": float(ap),
        "event_recall": float(ev_recall),
        "false_positive_rate": float(threshold["fpr"]),
        "specificity": float(threshold["specificity"]),
        "threshold": float(threshold["threshold"]),
        "event_peaks": {k: (None if v is None else float(v)) for k,v in peaks.items()},
    }

def candidate_configs(config, policy):
    base_weights = config["market_weights"]
    out = []

    # One-point transfer preserves total market weight and makes each cycle deliberately small.
    step = int(policy["candidate_generation"]["weight_step"])
    lo = int(policy["candidate_generation"]["min_market_weight"])
    hi = int(policy["candidate_generation"]["max_market_weight"])
    for donor in MARKET_KEYS:
        for receiver in MARKET_KEYS:
            if donor == receiver:
                continue
            if base_weights[donor]-step < lo or base_weights[receiver]+step > hi:
                continue
            cand = deepcopy(config)
            cand["market_weights"][donor] -= step
            cand["market_weights"][receiver] += step
            out.append({
                "kind": "market_weight_transfer",
                "description": f"{donor} -{step}, {receiver} +{step}",
                "config": cand,
            })

    max_hybrid_step = float(policy["candidate_generation"].get("max_hybrid_step", 0.05))
    current_nn_weight = float(config["hybrid"]["nn_weight"])
    for nn_weight in policy["candidate_generation"]["hybrid_nn_candidates"]:
        if abs(float(nn_weight)-current_nn_weight) < 1e-9:
            continue
        if abs(float(nn_weight)-current_nn_weight) > max_hybrid_step + 1e-9:
            continue
        cand = deepcopy(config)
        cand["hybrid"]["nn_weight"] = float(nn_weight)
        cand["hybrid"]["rule_weight"] = round(1.0-float(nn_weight), 6)
        out.append({
            "kind": "hybrid_mix",
            "description": f"NN weight {config['hybrid']['nn_weight']:.2f} -> {nn_weight:.2f}",
            "config": cand,
        })
    return out

def guardrails(baseline, candidate, policy):
    acc = policy["acceptance"]
    reasons = []
    if candidate["objective"] - baseline["objective"] < float(acc["min_objective_improvement"]):
        reasons.append("objective improvement below minimum")
    if candidate["false_positive_rate"] - baseline["false_positive_rate"] > float(acc["max_false_positive_rate_increase"]):
        reasons.append("false-positive rate regression")
    if candidate["event_recall"] < float(acc["min_event_recall"]):
        reasons.append("event recall below minimum")
    max_reg = float(acc["max_event_peak_regression"])
    for key, base_peak in baseline["event_peaks"].items():
        cand_peak = candidate["event_peaks"].get(key)
        if base_peak is not None and cand_peak is not None and base_peak-cand_peak > max_reg:
            reasons.append(f"{key} peak regression > {max_reg}")
    return len(reasons) == 0, reasons

def summarize_change(old, new):
    changes = []
    for k in MARKET_KEYS:
        if old["market_weights"][k] != new["market_weights"][k]:
            changes.append({
                "field": f"market_weights.{k}",
                "from": old["market_weights"][k],
                "to": new["market_weights"][k]
            })
    for k in ["rule_weight","nn_weight"]:
        if float(old["hybrid"][k]) != float(new["hybrid"][k]):
            changes.append({
                "field": f"hybrid.{k}",
                "from": old["hybrid"][k],
                "to": new["hybrid"][k]
            })
    return changes

def main():
    now = datetime.now(timezone.utc)
    policy = read_json(POLICY_PATH, {})
    config = read_json(CONFIG_PATH, {})
    bt = read_json(BACKTEST_PATH, {})
    nn = read_json(NN_PATH, {})
    windows_cfg = read_json(WINDOWS_PATH, {})
    windows = windows_cfg.get("windows", [])

    if not policy.get("enabled", False):
        state = {"version":1,"updated_at":now.isoformat(),"decision":"disabled"}
        write_json(STATE_JSON,state)
        STATE_JS.write_text("window.__AGENT_STATE__ = "+json.dumps(state,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")
        return

    cutoff = parse_day(policy["optimization_cutoff"])
    lead_days = int(policy["lead_days"])
    rows = [
        r for r in bt.get("series", [])
        if r.get("date") and parse_day(r["date"]) <= cutoff and float(r.get("coverage_pct") or 0) >= 55
    ]
    if len(rows) < 500:
        raise RuntimeError("Insufficient calibration rows for self-improvement agent")

    y = np.asarray([label_day(parse_day(r["date"]), windows, lead_days) for r in rows], dtype=np.int64)
    X = np.stack([nn_features(r) for r in rows])
    models = load_models(nn)
    if len(models) < 3:
        raise RuntimeError("Neural ensemble unavailable")
    nn_pred = ensemble_predict(models, X)

    objective_weights = policy["objective_weights"]
    baseline = evaluate(
        rows,y,nn_pred,windows,
        config["market_weights"],float(config["hybrid"]["nn_weight"]),objective_weights
    )

    candidates = []
    for spec in candidate_configs(config,policy):
        cand_cfg = spec["config"]
        metrics = evaluate(
            rows,y,nn_pred,windows,
            cand_cfg["market_weights"],float(cand_cfg["hybrid"]["nn_weight"]),objective_weights
        )
        accepted_by_guard, reasons = guardrails(baseline,metrics,policy)
        candidates.append({
            "kind":spec["kind"],
            "description":spec["description"],
            "metrics":metrics,
            "passes_guardrails":accepted_by_guard,
            "rejection_reasons":reasons,
            "config":cand_cfg,
        })

    candidates.sort(key=lambda x:x["metrics"]["objective"], reverse=True)
    winner = next((x for x in candidates if x["passes_guardrails"]), None)

    new_config = deepcopy(config)
    decision = "reject_all"
    accepted_change = None
    if winner is not None:
        new_config = winner["config"]
        new_config["source"] = "self_improvement_agent"
        new_config["last_agent_change"] = {
            "at": now.isoformat().replace("+00:00","Z"),
            "description": winner["description"],
            "baseline_objective": round(baseline["objective"],6),
            "candidate_objective": round(winner["metrics"]["objective"],6),
        }
        write_json(CONFIG_PATH,new_config)
        decision = "accepted"
        accepted_change = {
            "description":winner["description"],
            "changes":summarize_change(config,new_config),
            "metrics":winner["metrics"],
        }

    # Holdout is report-only and cannot affect winner selection.
    holdout_start = parse_day(policy["holdout_start"])
    holdout_rows = [r for r in bt.get("series", []) if r.get("date") and parse_day(r["date"]) >= holdout_start]
    holdout_report = None
    if holdout_rows:
        hy = np.asarray([label_day(parse_day(r["date"]), windows, lead_days) for r in holdout_rows], dtype=np.int64)
        hX = np.stack([nn_features(r) for r in holdout_rows])
        hp = ensemble_predict(models,hX)
        holdout_report = {
            "incumbent": evaluate(
                holdout_rows,hy,hp,windows,config["market_weights"],
                float(config["hybrid"]["nn_weight"]),objective_weights
            ),
            "post_decision": evaluate(
                holdout_rows,hy,hp,windows,new_config["market_weights"],
                float(new_config["hybrid"]["nn_weight"]),objective_weights
            ),
            "used_for_selection": False,
        }

    state = {
        "version":1,
        "updated_at":now.isoformat().replace("+00:00","Z"),
        "decision":decision,
        "policy_summary":{
            "optimization_cutoff":policy["optimization_cutoff"],
            "holdout_start":policy["holdout_start"],
            "holdout_used_for_selection":False,
            "allow_code_rewrite":False,
            "max_changes_per_cycle":1,
        },
        "baseline":baseline,
        "accepted_change":accepted_change,
        "candidate_count":len(candidates),
        "top_candidates":[
            {
                "kind":x["kind"],
                "description":x["description"],
                "objective":round(x["metrics"]["objective"],6),
                "improvement":round(x["metrics"]["objective"]-baseline["objective"],6),
                "passes_guardrails":x["passes_guardrails"],
                "rejection_reasons":x["rejection_reasons"],
                "fpr":round(x["metrics"]["false_positive_rate"],6),
                "event_recall":round(x["metrics"]["event_recall"],6),
            }
            for x in candidates[:10]
        ],
        "active_config":new_config,
        "holdout_report":holdout_report,
    }
    write_json(STATE_JSON,state)
    STATE_JS.write_text("window.__AGENT_STATE__ = "+json.dumps(state,ensure_ascii=False,indent=2)+";\n",encoding="utf-8")

    history = read_json(HISTORY_PATH, [])
    history.append({
        "updated_at":state["updated_at"],
        "decision":decision,
        "accepted_change":accepted_change,
        "baseline_objective":baseline["objective"],
        "active_config":new_config,
    })
    write_json(HISTORY_PATH,history[-100:])

    print(json.dumps({
        "decision":decision,
        "baseline_objective":round(baseline["objective"],6),
        "winner":None if accepted_change is None else accepted_change["description"],
        "winner_objective":None if accepted_change is None else round(accepted_change["metrics"]["objective"],6),
        "candidate_count":len(candidates),
        "holdout_used_for_selection":False,
    },ensure_ascii=False))

if __name__ == "__main__":
    main()
