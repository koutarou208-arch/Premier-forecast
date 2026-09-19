#!/usr/bin/env python3
import json
import math
import pathlib
import re
from copy import deepcopy
from datetime import date, timedelta

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKTEST = ROOT / "data" / "backtest.json"
CONFIG = ROOT / "data" / "backtest_config.json"
LATEST = ROOT / "data" / "latest.js"
MODEL_CONFIG = ROOT / "data" / "model_config.json"
OUT_JSON = ROOT / "data" / "nn_model.json"
OUT_JS = ROOT / "data" / "nn_model.js"

CHANNELS = [
    "ig_credit", "hy_credit", "leveraged_credit", "financial_stress",
    "rates_liquidity", "funding_market", "banking_stress", "europe", "energy"
]
BASE_FEATURES = CHANNELS + ["breadth", "raw_score", "coverage_pct"]
FEATURES = BASE_FEATURES + [f"missing_{x}" for x in CHANNELS]

TRAIN_END = date(2019, 12, 31)
VAL_END = date(2022, 12, 31)
LEAD_DAYS = 60
ENSEMBLE_SEEDS = [11, 29, 47, 71, 101]

def parse_day(s):
    return date.fromisoformat(s)

def load_latest():
    text = LATEST.read_text(encoding="utf-8")
    m = re.search(r"window.__RISK_DATA__\s*=\s*(\{.*\});\s*$", text, re.S)
    if not m:
        raise RuntimeError("latest.js payload missing")
    return json.loads(m.group(1))

def label_day(day, windows):
    for w in windows:
        start = parse_day(w["start"]) - timedelta(days=LEAD_DAYS)
        end = parse_day(w["end"])
        if start <= day <= end:
            return 1
    return 0

def row_features(row):
    channels = row.get("channels", {})
    values = []
    missing = []
    for key in CHANNELS:
        value = channels.get(key)
        missing.append(1.0 if value is None else 0.0)
        values.append(0.0 if value is None else np.clip(float(value) / 100.0, 0.0, 1.0))
    values.extend([
        0.0 if row.get("breadth") is None else np.clip(float(row["breadth"]) / 100.0, 0.0, 1.0),
        0.0 if row.get("raw_score") is None else np.clip(float(row["raw_score"]) / 100.0, 0.0, 1.0),
        0.0 if row.get("coverage_pct") is None else np.clip(float(row["coverage_pct"]) / 100.0, 0.0, 1.0),
    ])
    values.extend(missing)
    return np.asarray(values, dtype=np.float64)

def current_features(latest):
    score_map = {x["id"]: x.get("score") for x in latest.get("indicators", [])}
    values, missing = [], []
    for key in CHANNELS:
        value = score_map.get(key)
        missing.append(1.0 if value is None else 0.0)
        values.append(0.0 if value is None else np.clip(float(value) / 100.0, 0.0, 1.0))
    breadth = (latest.get("breadth") or {}).get("score")
    values.extend([
        0.0 if breadth is None else np.clip(float(breadth) / 100.0, 0.0, 1.0),
        0.0 if latest.get("market_raw_score") is None else np.clip(float(latest["market_raw_score"]) / 100.0, 0.0, 1.0),
        0.0 if latest.get("market_coverage_pct") is None else np.clip(float(latest["market_coverage_pct"]) / 100.0, 0.0, 1.0),
    ])
    values.extend(missing)
    return np.asarray(values, dtype=np.float64)

def sigmoid(x):
    x = np.clip(x, -35.0, 35.0)
    return 1.0 / (1.0 + np.exp(-x))

def init_model(rng, n_in, h1=12, h2=6):
    def xavier(a, b):
        lim = math.sqrt(6.0 / (a + b))
        return rng.uniform(-lim, lim, size=(a, b))
    return {
        "w1": xavier(n_in, h1), "b1": np.zeros(h1),
        "w2": xavier(h1, h2), "b2": np.zeros(h2),
        "w3": xavier(h2, 1), "b3": np.zeros(1),
    }

def forward(model, X):
    z1 = X @ model["w1"] + model["b1"]
    a1 = np.tanh(z1)
    z2 = a1 @ model["w2"] + model["b2"]
    a2 = np.tanh(z2)
    z3 = a2 @ model["w3"] + model["b3"]
    p = sigmoid(z3).reshape(-1)
    return p, (X, a1, a2)

def balanced_bce(y, p, pos_weight):
    eps = 1e-8
    weights = np.where(y > 0.5, pos_weight, 1.0)
    return float(np.mean(weights * (-(y*np.log(p+eps) + (1-y)*np.log(1-p+eps)))))

def train_one(X, y, Xv, yv, seed):
    rng = np.random.default_rng(seed)
    model = init_model(rng, X.shape[1])
    pos = max(1, int(np.sum(y == 1)))
    neg = max(1, int(np.sum(y == 0)))
    pos_weight = min(8.0, neg / pos)

    lr = 0.035
    l2 = 0.0015
    best = deepcopy(model)
    best_loss = float("inf")
    stale = 0

    for epoch in range(1400):
        p, (Xin, a1, a2) = forward(model, X)
        sample_w = np.where(y > 0.5, pos_weight, 1.0)
        dz3 = ((p - y) * sample_w / len(y)).reshape(-1, 1)

        dw3 = a2.T @ dz3 + l2 * model["w3"]
        db3 = np.sum(dz3, axis=0)
        da2 = dz3 @ model["w3"].T
        dz2 = da2 * (1.0 - a2*a2)
        dw2 = a1.T @ dz2 + l2 * model["w2"]
        db2 = np.sum(dz2, axis=0)
        da1 = dz2 @ model["w2"].T
        dz1 = da1 * (1.0 - a1*a1)
        dw1 = Xin.T @ dz1 + l2 * model["w1"]
        db1 = np.sum(dz1, axis=0)

        for k, g in [("w1",dw1),("b1",db1),("w2",dw2),("b2",db2),("w3",dw3),("b3",db3)]:
            model[k] -= lr * np.clip(g, -2.0, 2.0)

        if epoch % 10 == 0:
            pv, _ = forward(model, Xv)
            val_loss = balanced_bce(yv, pv, pos_weight)
            if val_loss + 1e-5 < best_loss:
                best_loss = val_loss
                best = deepcopy(model)
                stale = 0
            else:
                stale += 1
            if stale >= 35:
                break
            if stale and stale % 12 == 0:
                lr *= 0.7
    return best, {"seed": seed, "best_val_loss": round(best_loss, 6), "epochs": epoch + 1, "pos_weight": round(pos_weight, 3)}

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
    total_pos = int(np.sum(yy))
    if total_pos == 0:
        return None
    tp = 0
    acc = 0.0
    for rank, label in enumerate(yy, start=1):
        if label == 1:
            tp += 1
            acc += tp / rank
    return acc / total_pos

def brier(y, p):
    return float(np.mean((p-y)**2)) if len(y) else None

def threshold_metrics(y, p, threshold):
    pred = p >= threshold
    pos = y == 1
    neg = ~pos
    tp = int(np.sum(pred & pos))
    fn = int(np.sum((~pred) & pos))
    fp = int(np.sum(pred & neg))
    tn = int(np.sum((~pred) & neg))
    recall = tp / (tp+fn) if tp+fn else None
    fpr = fp / (fp+tn) if fp+tn else None
    precision = tp / (tp+fp) if tp+fp else None
    balanced = None if recall is None or fpr is None else 0.5*(recall + (1-fpr))
    return {
        "threshold": round(float(threshold), 3),
        "recall": None if recall is None else round(recall, 4),
        "false_positive_rate": None if fpr is None else round(fpr, 4),
        "precision": None if precision is None else round(precision, 4),
        "balanced_accuracy": None if balanced is None else round(balanced, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }

def choose_threshold(y, p):
    candidates = np.linspace(0.20, 0.80, 61)
    scored = [threshold_metrics(y,p,t) for t in candidates]
    valid = [x for x in scored if x["balanced_accuracy"] is not None]
    best = max(valid, key=lambda x: (x["balanced_accuracy"], -(x["false_positive_rate"] or 0))) if valid else threshold_metrics(y,p,0.5)
    return best

def ensemble_predict(models, X):
    preds = np.stack([forward(m, X)[0] for m in models], axis=0)
    return preds.mean(axis=0), preds.std(axis=0)

def serialize_model(model):
    return {k: np.asarray(v).round(8).tolist() for k,v in model.items()}

def local_sensitivity(models, x):
    base, _ = ensemble_predict(models, x.reshape(1,-1))
    base = float(base[0])
    drivers = []
    for i, name in enumerate(BASE_FEATURES):
        xp = x.copy()
        xp[i] = 0.0
        pred, _ = ensemble_predict(models, xp.reshape(1,-1))
        delta = base - float(pred[0])
        drivers.append({"feature": name, "delta_score": round(delta*100.0, 2)})
    return sorted(drivers, key=lambda z: abs(z["delta_score"]), reverse=True)[:6]

def event_eval(rows, preds, windows, threshold):
    out = []
    for w in windows:
        start = parse_day(w["start"])
        end = parse_day(w["end"])
        idx = [i for i,r in enumerate(rows) if start <= parse_day(r["date"]) <= end]
        if not idx:
            continue
        vals = [(rows[i]["date"], float(preds[i])) for i in idx]
        peak_date, peak = max(vals, key=lambda x:x[1])
        first = next((d for d,p in vals if p >= threshold), None)
        out.append({
            "id": w["id"], "name": w["name"], "group": w["group"],
            "peak_nn_score": round(peak*100.0, 1),
            "peak_date": peak_date,
            "first_alert": first,
        })
    return out

def main():
    bt = json.loads(BACKTEST.read_text(encoding="utf-8"))
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    latest = load_latest()
    rows = [r for r in bt.get("series", []) if r.get("date") and r.get("coverage_pct",0) >= 55]
    if len(rows) < 500:
        raise RuntimeError("Insufficient historical rows for NN training")

    X = np.stack([row_features(r) for r in rows])
    y = np.asarray([label_day(parse_day(r["date"]), cfg["windows"]) for r in rows], dtype=np.float64)
    dates = np.asarray([parse_day(r["date"]) for r in rows], dtype=object)

    train_mask = dates <= TRAIN_END
    val_mask = (dates > TRAIN_END) & (dates <= VAL_END)
    test_mask = dates > VAL_END
    if np.sum(y[train_mask]) < 20 or np.sum(y[val_mask]) < 5 or np.sum(test_mask) < 50:
        raise RuntimeError("Temporal split has insufficient positive/holdout observations")

    models = []
    training = []
    for seed in ENSEMBLE_SEEDS:
        model, meta = train_one(X[train_mask], y[train_mask], X[val_mask], y[val_mask], seed)
        models.append(model)
        training.append(meta)

    pred_all, std_all = ensemble_predict(models, X)
    pred_train, _ = ensemble_predict(models, X[train_mask])
    pred_val, _ = ensemble_predict(models, X[val_mask])
    pred_test, _ = ensemble_predict(models, X[test_mask])

    selected = choose_threshold(y[val_mask], pred_val)
    threshold = selected["threshold"]

    def metrics(mask, pred):
        yy = y[mask]
        return {
            "observations": int(len(yy)),
            "positive_rate": round(float(np.mean(yy)),4),
            "roc_auc": None if roc_auc(yy,pred) is None else round(float(roc_auc(yy,pred)),4),
            "average_precision": None if average_precision(yy,pred) is None else round(float(average_precision(yy,pred)),4),
            "brier": None if brier(yy,pred) is None else round(float(brier(yy,pred)),4),
            "at_selected_threshold": threshold_metrics(yy,pred,threshold),
        }

    hist_x = row_features(rows[-1])
    hist_pred, hist_std = ensemble_predict(models, hist_x.reshape(1,-1))
    prod_x = current_features(latest)
    prod_pred, prod_std = ensemble_predict(models, prod_x.reshape(1,-1))

    nn_prod = float(prod_pred[0]) * 100.0
    nn_hist = float(hist_pred[0]) * 100.0
    rule_market = latest.get("market_score")
    model_cfg = json.loads(MODEL_CONFIG.read_text(encoding="utf-8")) if MODEL_CONFIG.exists() else {}
    hybrid_cfg = model_cfg.get("hybrid", {})
    rule_weight = float(hybrid_cfg.get("rule_weight", 0.65))
    nn_weight = float(hybrid_cfg.get("nn_weight", 0.35))
    total_mix = rule_weight + nn_weight
    if total_mix <= 0:
        rule_weight, nn_weight, total_mix = 0.65, 0.35, 1.0
    rule_weight /= total_mix
    nn_weight /= total_mix
    hybrid_market = None if rule_market is None else rule_weight*float(rule_market) + nn_weight*nn_prod

    payload = {
        "version": 6,
        "model_type": "MLP ensemble",
        "architecture": [len(FEATURES), 12, 6, 1],
        "activation": "tanh/tanh/sigmoid",
        "ensemble_size": len(models),
        "active_model_config": model_cfg,
        "hybrid_mix": {"rule_weight": round(rule_weight,4), "nn_weight": round(nn_weight,4)},
        "target": f"inside labeled stress window or within {LEAD_DAYS} calendar days before its start",
        "temporal_split": {
            "train": f"<= {TRAIN_END.isoformat()}",
            "validation": f"2020-01-01..{VAL_END.isoformat()}",
            "test_holdout": ">= 2023-01-01",
        },
        "features": FEATURES,
        "training": training,
        "selected_threshold": threshold,
        "validation_threshold_selection": selected,
        "metrics": {
            "train": metrics(train_mask,pred_train),
            "validation": metrics(val_mask,pred_val),
            "test_holdout": metrics(test_mask,pred_test),
        },
        "current": {
            "production_nn_score": round(nn_prod,1),
            "production_uncertainty_std": round(float(prod_std[0])*100.0,2),
            "historical_comparable_nn_score": round(nn_hist,1),
            "historical_comparable_uncertainty_std": round(float(hist_std[0])*100.0,2),
            "rule_market_score": rule_market,
            "hybrid_market_score": None if hybrid_market is None else round(hybrid_market,1),
            "alert": bool(float(prod_pred[0]) >= threshold),
            "threshold_score": round(threshold*100.0,1),
            "top_local_sensitivities": local_sensitivity(models,prod_x),
        },
        "event_evaluation": event_eval(rows,pred_all,cfg["windows"],threshold),
        "limitations": [
            "Historical credit channels use long-history proxies rather than the exact current ICE BofA production series.",
            "Crisis labels are expert-defined windows, so the output is an early-warning score, not a literal probability of crisis.",
            "Observations within each event are serially correlated; headline sample counts overstate independent crisis examples.",
            "Stage 0-4 remains deterministic and cannot be upgraded by the neural network alone.",
        ],
        "models": [serialize_model(m) for m in models],
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    OUT_JS.write_text("window.__NN_DATA__ = "+json.dumps(payload,ensure_ascii=False,indent=2)+";\n", encoding="utf-8")
    print(json.dumps({
        "version":6,
        "production_nn_score":payload["current"]["production_nn_score"],
        "hybrid_market_score":payload["current"]["hybrid_market_score"],
        "threshold":payload["current"]["threshold_score"],
        "validation_auc":payload["metrics"]["validation"]["roc_auc"],
        "test_auc":payload["metrics"]["test_holdout"]["roc_auc"],
        "test_brier":payload["metrics"]["test_holdout"]["brier"],
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
