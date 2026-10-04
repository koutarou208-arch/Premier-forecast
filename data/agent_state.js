window.__AGENT_STATE__ = {
  "version": 1,
  "updated_at": "2026-10-04T02:20:35.676639Z",
  "decision": "reject_all",
  "policy_summary": {
    "optimization_cutoff": "2022-12-31",
    "holdout_start": "2023-01-01",
    "holdout_used_for_selection": false,
    "allow_code_rewrite": false,
    "max_changes_per_cycle": 1
  },
  "baseline": {
    "objective": 0.8678968066152192,
    "roc_auc": 0.8726917780811599,
    "average_precision": 0.9265629231937641,
    "event_recall": 0.75,
    "false_positive_rate": 0.09593023255813954,
    "specificity": 0.9040697674418605,
    "threshold": 34.0,
    "event_peaks": {
      "gfc": 93.80104153251142,
      "euro": 53.12472307960786,
      "repo2019": 20.41336823162971,
      "covid": 80.43705253512789
    }
  },
  "accepted_change": null,
  "candidate_count": 74,
  "top_candidates": [
    {
      "kind": "market_weight_transfer",
      "description": "banking_stress -1, europe +1",
      "objective": 0.869302,
      "improvement": 0.001405,
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
      "objective": 0.8693,
      "improvement": 0.001403,
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
      "objective": 0.869285,
      "improvement": 0.001388,
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
      "objective": 0.869189,
      "improvement": 0.001292,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.09157,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, europe +1",
      "objective": 0.869158,
      "improvement": 0.001261,
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
      "objective": 0.868908,
      "improvement": 0.001011,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.093023,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "ig_credit -1, europe +1",
      "objective": 0.868862,
      "improvement": 0.000965,
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
      "objective": 0.868822,
      "improvement": 0.000925,
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
      "objective": 0.868561,
      "improvement": 0.000664,
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
      "objective": 0.868538,
      "improvement": 0.000641,
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
      "objective": 0.700738123507654,
      "roc_auc": 0.8977674624226348,
      "average_precision": 0.7966527592826053,
      "event_recall": 0.0,
      "false_positive_rate": 0.06321839080459771,
      "specificity": 0.9367816091954023,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "post_decision": {
      "objective": 0.700738123507654,
      "roc_auc": 0.8977674624226348,
      "average_precision": 0.7966527592826053,
      "event_recall": 0.0,
      "false_positive_rate": 0.06321839080459771,
      "specificity": 0.9367816091954023,
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
