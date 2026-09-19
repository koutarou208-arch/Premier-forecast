window.__AGENT_STATE__ = {
  "version": 1,
  "updated_at": "2026-09-19T16:00:57.446038Z",
  "decision": "accepted",
  "policy_summary": {
    "optimization_cutoff": "2022-12-31",
    "holdout_start": "2023-01-01",
    "holdout_used_for_selection": false,
    "allow_code_rewrite": false,
    "max_changes_per_cycle": 1
  },
  "baseline": {
    "objective": 0.857333631219731,
    "roc_auc": 0.8693346318614067,
    "average_precision": 0.9238939472496988,
    "event_recall": 0.75,
    "false_positive_rate": 0.13953488372093023,
    "specificity": 0.8604651162790697,
    "threshold": 29.5,
    "event_peaks": {
      "gfc": 93.68098674258621,
      "euro": 50.42705294957392,
      "repo2019": 20.657102574500264,
      "covid": 79.49132336448307
    }
  },
  "accepted_change": {
    "description": "NN weight 0.35 -> 0.40",
    "changes": [
      {
        "field": "hybrid.rule_weight",
        "from": 0.65,
        "to": 0.6
      },
      {
        "field": "hybrid.nn_weight",
        "from": 0.35,
        "to": 0.4
      }
    ],
    "metrics": {
      "objective": 0.870146212773825,
      "roc_auc": 0.8735700499011393,
      "average_precision": 0.9273542230941699,
      "event_recall": 0.75,
      "false_positive_rate": 0.0872093023255814,
      "specificity": 0.9127906976744186,
      "threshold": 34.5,
      "event_peaks": {
        "gfc": 93.80172735307912,
        "euro": 53.25649084889577,
        "repo2019": 20.336512289728695,
        "covid": 80.44193569697535
      }
    }
  },
  "candidate_count": 74,
  "top_candidates": [
    {
      "kind": "hybrid_mix",
      "description": "NN weight 0.35 -> 0.40",
      "objective": 0.870146,
      "improvement": 0.012813,
      "passes_guardrails": true,
      "rejection_reasons": [],
      "fpr": 0.087209,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "financial_stress -1, banking_stress +1",
      "objective": 0.861127,
      "improvement": 0.003793,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.119186,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, funding_market +1",
      "objective": 0.859144,
      "improvement": 0.001811,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.130814,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, ig_credit +1",
      "objective": 0.858984,
      "improvement": 0.00165,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.132267,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "ig_credit -1, leveraged_credit +1",
      "objective": 0.858935,
      "improvement": 0.001601,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.130814,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "banking_stress -1, funding_market +1",
      "objective": 0.858927,
      "improvement": 0.001594,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.132267,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "ig_credit -1, hy_credit +1",
      "objective": 0.85885,
      "improvement": 0.001516,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.130814,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "financial_stress -1, europe +1",
      "objective": 0.858779,
      "improvement": 0.001445,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.135174,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "rates_liquidity -1, europe +1",
      "objective": 0.858661,
      "improvement": 0.001327,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.136628,
      "event_recall": 0.75
    },
    {
      "kind": "market_weight_transfer",
      "description": "funding_market -1, energy +1",
      "objective": 0.858658,
      "improvement": 0.001324,
      "passes_guardrails": false,
      "rejection_reasons": [
        "objective improvement below minimum"
      ],
      "fpr": 0.132267,
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
      "objective": 0.6993912181571483,
      "roc_auc": 0.893448121645796,
      "average_precision": 0.7979002930221533,
      "event_recall": 0.0,
      "false_positive_rate": 0.06395348837209303,
      "specificity": 0.936046511627907,
      "threshold": 20.0,
      "event_peaks": {
        "gfc": null,
        "euro": null,
        "repo2019": null,
        "covid": null
      }
    },
    "post_decision": {
      "objective": 0.6967219227634436,
      "roc_auc": 0.8905970483005367,
      "average_precision": 0.7912146141306977,
      "event_recall": 0.0,
      "false_positive_rate": 0.06395348837209303,
      "specificity": 0.936046511627907,
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
