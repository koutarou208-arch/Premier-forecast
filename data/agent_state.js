window.__AGENT_STATE__ = {
  "version": 1,
  "updated_at": "2026-10-11T01:31:39.170883Z",
  "decision": "reject_all",
  "policy_summary": {
    "optimization_cutoff": "2022-12-31",
    "holdout_start": "2023-01-01",
    "holdout_used_for_selection": false,
    "allow_code_rewrite": false,
    "max_changes_per_cycle": 1
  },
  "baseline": {
    "objective": 0.8701458638309654,
    "roc_auc": 0.8735715210432162,
    "average_precision": 0.9273507677238236,
    "event_recall": 0.75,
    "false_positive_rate": 0.0872093023255814,
    "specificity": 0.9127906976744186,
    "threshold": 34.5,
    "event_peaks": {
      "gfc": 93.80171595395618,
      "euro": 53.25570632670673,
      "repo2019": 20.377590114960988,
      "covid": 80.44246705267368
    }
  },
  "accepted_change": null,
  "candidate_count": 74,
  "top_candidates": [
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, europe +1",
      "objective": 0.871436,
      "improvement": 0.00129,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.082849,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "banking_stress -1, europe +1",
      "objective": 0.871287,
      "improvement": 0.001141,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.084302,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "hy_credit -1, europe +1",
      "objective": 0.870669,
      "improvement": 0.000524,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, europe +1",
      "objective": 0.870636,
      "improvement": 0.00049,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "leveraged_credit -1, europe +1",
      "objective": 0.870597,
      "improvement": 0.000451,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "ig_credit -1, europe +1",
      "objective": 0.870531,
      "improvement": 0.000385,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "financial_stress -1, europe +1",
      "objective": 0.870529,
      "improvement": 0.000383,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, leveraged_credit +1",
      "objective": 0.870463,
      "improvement": 0.000317,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.085756,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, hy_credit +1",
      "objective": 0.870381,
      "improvement": 0.000235,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.085756,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, banking_stress +1",
      "objective": 0.870335,
      "improvement": 0.000189,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.085756,
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
      "objective": 0.6966366012136871,
      "roc_auc": 0.8906043956043956,
      "average_precision": 0.7899859652943086,
      "event_recall": 0.0,
      "false_positive_rate": 0.06285714285714286,
      "specificity": 0.9371428571428572,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "post_decision": {
      "objective": 0.6966366012136871,
      "roc_auc": 0.8906043956043956,
      "average_precision": 0.7899859652943086,
      "event_recall": 0.0,
      "false_positive_rate": 0.06285714285714286,
      "specificity": 0.9371428571428572,
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
