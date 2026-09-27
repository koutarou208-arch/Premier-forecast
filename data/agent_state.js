window.__AGENT_STATE__ = {
  "version": 1,
  "updated_at": "2026-09-27T01:04:09.711704Z",
  "decision": "reject_all",
  "policy_summary": {
    "optimization_cutoff": "2022-12-31",
    "holdout_start": "2023-01-01",
    "holdout_used_for_selection": false,
    "allow_code_rewrite": false,
    "max_changes_per_cycle": 1
  },
  "baseline": {
    "objective": 0.8701692886076415,
    "roc_auc": 0.87362889558422,
    "average_precision": 0.9273641424731232,
    "event_recall": 0.75,
    "false_positive_rate": 0.0872093023255814,
    "specificity": 0.9127906976744186,
    "threshold": 34.5,
    "event_peaks": {
      "gfc": 93.80247757497736,
      "euro": 53.21769104922042,
      "repo2019": 20.35326888085368,
      "covid": 80.44230626553811
    }
  },
  "accepted_change": null,
  "candidate_count": 74,
  "top_candidates": [
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, europe +1",
      "objective": 0.871415,
      "improvement": 0.001245,
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
      "objective": 0.871288,
      "improvement": 0.001119,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.084302,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "financial_stress -1, europe +1",
      "objective": 0.871121,
      "improvement": 0.000952,
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
      "objective": 0.87067,
      "improvement": 0.000501,
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
      "objective": 0.870647,
      "improvement": 0.000478,
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
      "objective": 0.870599,
      "improvement": 0.00043,
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
      "objective": 0.870532,
      "improvement": 0.000363,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "energy -1, europe +1",
      "objective": 0.870404,
      "improvement": 0.000234,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.088663,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, hy_credit +1",
      "objective": 0.870395,
      "improvement": 0.000226,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.085756,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "hy_credit -1, financial_stress +1",
      "objective": 0.870321,
      "improvement": 0.000152,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.087209,
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
      "objective": 0.6964189875603106,
      "roc_auc": 0.8901734104046243,
      "average_precision": 0.7903002276978897,
      "event_recall": 0.0,
      "false_positive_rate": 0.06358381502890173,
      "specificity": 0.9364161849710982,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "post_decision": {
      "objective": 0.6964189875603106,
      "roc_auc": 0.8901734104046243,
      "average_precision": 0.7903002276978897,
      "event_recall": 0.0,
      "false_positive_rate": 0.06358381502890173,
      "specificity": 0.9364161849710982,
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
