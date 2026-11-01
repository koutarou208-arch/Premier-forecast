window.__AGENT_STATE__ = {
  "version": 1,
  "updated_at": "2026-11-01T01:48:29.052869Z",
  "decision": "reject_all",
  "policy_summary": {
    "optimization_cutoff": "2022-12-31",
    "holdout_start": "2023-01-01",
    "holdout_used_for_selection": false,
    "allow_code_rewrite": false,
    "max_changes_per_cycle": 1
  },
  "baseline": {
    "objective": 0.8678277884442158,
    "roc_auc": 0.8725520195838433,
    "average_precision": 0.926482512405994,
    "event_recall": 0.75,
    "false_positive_rate": 0.09593023255813954,
    "specificity": 0.9040697674418605,
    "threshold": 34.0,
    "event_peaks": {
      "gfc": 93.79873606351936,
      "euro": 53.089462512960935,
      "repo2019": 20.529704274496183,
      "covid": 80.4349531227967
    }
  },
  "accepted_change": null,
  "candidate_count": 74,
  "top_candidates": [
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, europe +1",
      "objective": 0.869407,
      "improvement": 0.001579,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.090116,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "banking_stress -1, europe +1",
      "objective": 0.869247,
      "improvement": 0.001419,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "energy -1, europe +1",
      "objective": 0.869232,
      "improvement": 0.001404,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "hy_credit -1, europe +1",
      "objective": 0.869223,
      "improvement": 0.001395,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, europe +1",
      "objective": 0.869137,
      "improvement": 0.001309,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "leveraged_credit -1, europe +1",
      "objective": 0.869131,
      "improvement": 0.001303,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "ig_credit -1, europe +1",
      "objective": 0.868797,
      "improvement": 0.000969,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.093023,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "financial_stress -1, europe +1",
      "objective": 0.868765,
      "improvement": 0.000937,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.093023,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, financial_stress +1",
      "objective": 0.868499,
      "improvement": 0.000671,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.093023,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, ig_credit +1",
      "objective": 0.868464,
      "improvement": 0.000636,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.093023,
      "event_recall": 0.75
    }
  ],
  "active_config": {
    "version": 1,
    "market_weights": {
      "ig_credit": 10,
      "hy_credit": 14,
      "leveraged_credit": 10,
      "financial_stress": 8,
      "rates_liquidity": 8,
      "funding_market": 10,
      "banking_stress": 8,
      "europe": 6,
      "energy": 7
    },
    "structural_weights": {
      "data_center": 6,
      "private_credit": 8,
      "bank_ai": 5
    },
    "hybrid": {
      "rule_weight": 0.6,
      "nn_weight": 0.4
    },
    "source": "self_improvement_agent",
    "last_agent_change": {
      "at": "2026-09-19T16:00:57.446038Z",
      "description": "NN weight 0.35 -> 0.40",
      "baseline_objective": 0.857334,
      "candidate_objective": 0.870146
    }
  },
  "holdout_report": {
    "incumbent": {
      "objective": 0.69836618940269,
      "roc_auc": 0.8945008643042351,
      "average_precision": 0.7906017498320217,
      "event_recall": 0.0,
      "false_positive_rate": 0.06179775280898876,
      "specificity": 0.9382022471910112,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "post_decision": {
      "objective": 0.69836618940269,
      "roc_auc": 0.8945008643042351,
      "average_precision": 0.7906017498320217,
      "event_recall": 0.0,
      "false_positive_rate": 0.06179775280898876,
      "specificity": 0.9382022471910112,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "used_for_selection": false
  }
};
