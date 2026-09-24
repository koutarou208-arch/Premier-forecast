window.__RISK_DATA__ = {
  "version": 6,
  "updated_at": "2026-09-24T01:30:13.007441Z",
  "score": 21.7,
  "raw_score": 21.7,
  "market_score": 11.7,
  "market_raw_score": 11.7,
  "market_coverage_pct": 100.0,
  "synchronization_bonus": 0.0,
  "level": "NORMAL",
  "summary": "NORMAL: AI/private-credit stress remains mainly sectoral; broad credit contagion is not yet confirmed.",
  "coverage_pct": 100.0,
  "breadth": {
    "score": 0.0,
    "stressed": 0,
    "available": 9,
    "severe": 0
  },
  "transmission": {
    "stage": 1,
    "label": "SECTOR REPRICING",
    "note": "AI/private-credit or banking channels are stressed, but broad contagion is not confirmed."
  },
  "flags": [
    {
      "type": "AI_CREDIT",
      "label": "AI / Private Credit stress is material"
    }
  ],
  "pillars": [
    {
      "name": "Broad Credit",
      "score": 14.2
    },
    {
      "name": "Funding / Liquidity",
      "score": 6.1
    },
    {
      "name": "Banking",
      "score": 34.1
    },
    {
      "name": "AI / Private Credit",
      "score": 63.4
    },
    {
      "name": "Europe / Energy",
      "score": 17.6
    }
  ],
  "weights": {
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
    "bank_ai": 5
  },
  "active_model_config": {
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
  "methodology": {
    "auto_components": {
      "level_weight": 45,
      "deviation_weight": 30,
      "velocity_weight": 25
    },
    "lookback_observations": 1260,
    "missing_data_policy": "exclude_and_renormalize",
    "event_decay": "confidence multiplier plus age-based decay after 30 days",
    "v4_layers": "SOFR-IORB funding, financial CP spread, CCC OAS, optional CDX/CLO/bank-CDS/BDC overrides",
    "v5_validation": "walk-forward historical backtest uses market-only score; no future observations are allowed",
    "v6_neural": "separate neural ensemble is trained on historical-comparable channel scores; deterministic Stage remains authoritative"
  },
  "diagnostics": {
    "us10y": 4.96,
    "us2y": 4.71,
    "curve_2s10s_bps": 25.0,
    "vix": 14.21,
    "realized_10y_vol_bps": 69.11866226775668,
    "move_manual": null,
    "italy_bund_bps": 80.59799999999998,
    "wti": 96.41,
    "gas": 2.9,
    "sofr": 3.87,
    "iorb": 3.9,
    "sofr_iorb_bps": -2.9999999999999805,
    "cpff": 0.19,
    "ccc_oas": 10.75,
    "cdx_hy_bps": null,
    "clo_aaa_bps": null,
    "clo_bbb_bps": null,
    "bank_cds_bps": null,
    "bdc_discount_pct": null
  },
  "data_failures": [],
  "indicators": [
    {
      "id": "ig_credit",
      "name": "US IG Corporate OAS",
      "score": 0.0,
      "value": "0.77%",
      "source": "FRED BAMLC0A0CM",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-22",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/series/BAMLC0A0CM",
      "note": "45% absolute level + 30% deviation from ~5y history + 25% 5/20-observation deterioration speed.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 13.5,
        "robust_z": -0.77,
        "delta_5": -0.03,
        "delta_20": -0.04,
        "velocity_pct_5": 21.3,
        "velocity_pct_20": 34.4
      },
      "quality": {}
    },
    {
      "id": "hy_credit",
      "name": "US High Yield OAS",
      "score": 0.0,
      "value": "2.68%",
      "source": "FRED BAMLH0A0HYM2",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-22",
      "weight": 14,
      "source_url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
      "note": "Core contagion channel. Fast widening can score high even before the absolute OAS reaches crisis thresholds.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 8.5,
        "robust_z": -1.06,
        "delta_5": -0.08,
        "delta_20": -0.02,
        "velocity_pct_5": 30.1,
        "velocity_pct_20": 59.7
      },
      "quality": {}
    },
    {
      "id": "leveraged_credit",
      "name": "Leveraged / Structured Credit",
      "score": 42.7,
      "value": "CCC OAS 10.75%",
      "source": "FRED CCC OAS + optional CDX/CLO",
      "mode": "AUTO/OVERRIDE",
      "as_of": "2026-09-22",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/series/BAMLH0A3HYC",
      "note": "CCC OAS is the automatic leveraged-credit proxy. Optional CDX HY and CLO AAA/BBB spreads can override when they show more stress.",
      "components": {
        "level": 22.9,
        "deviation": 95.3,
        "velocity": 15.5
      },
      "stats": {
        "ccc_oas": 10.75,
        "cdx_hy_bps": null,
        "clo_aaa_bps": null,
        "clo_bbb_bps": null
      },
      "quality": {}
    },
    {
      "id": "financial_stress",
      "name": "St. Louis Financial Stress",
      "score": 0.0,
      "value": "-0.91",
      "source": "FRED STLFSI4",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-18",
      "weight": 8,
      "source_url": "https://fred.stlouisfed.org/series/STLFSI4",
      "note": "Cross-market stress measured against both fixed anchors and its own recent distribution.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 2.3,
        "robust_z": -1.24,
        "delta_5": -0.098,
        "delta_20": 0.041,
        "velocity_pct_5": 35.9,
        "velocity_pct_20": 58.3
      },
      "quality": {}
    },
    {
      "id": "rates_liquidity",
      "name": "Treasury Vol / Liquidity",
      "score": 0.0,
      "value": "RV20 69.12 bp / VIX 14.21",
      "source": "FRED DGS10 + VIXCLS",
      "mode": "AUTO/HYBRID",
      "as_of": "2026-09-22",
      "weight": 8,
      "source_url": "https://fred.stlouisfed.org/series/DGS10",
      "note": "Uses the strongest signal from 10Y realized yield volatility, VIX, and optional MOVE. Missing inputs are not treated as zero.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "rv": 69.11866226775668,
        "move": null,
        "vix": 14.21
      },
      "quality": {}
    },
    {
      "id": "funding_market",
      "name": "Repo / Funding Market",
      "score": 18.3,
      "value": "-3.0 bp",
      "source": "FRED SOFR - IORB",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-22",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/graph/?id=SOFR,IORB",
      "note": "Positive SOFR-IORB pressure is monitored against absolute thresholds, its own distribution and deterioration velocity.",
      "components": {
        "level": 0.0,
        "deviation": 60.9,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 80.5,
        "robust_z": 2.02,
        "delta_5": -2.0,
        "delta_20": -3.0,
        "velocity_pct_5": 19.0,
        "velocity_pct_20": 12.8
      },
      "quality": {}
    },
    {
      "id": "banking_stress",
      "name": "Bank Short-term Funding",
      "score": 11.5,
      "value": "CP-FF 0.19%",
      "source": "FRED CPFF + optional bank CDS",
      "mode": "AUTO/OVERRIDE",
      "as_of": "2026-09-21",
      "weight": 8,
      "source_url": "https://fred.stlouisfed.org/series/CPFF",
      "note": "Financial commercial-paper spread is the public banking-funding proxy; an entered bank CDS reading overrides if more stressed.",
      "components": {
        "level": 0.0,
        "deviation": 38.3,
        "velocity": 0.0
      },
      "stats": {
        "cpff": 0.19,
        "bank_cds_bps": null
      },
      "quality": {}
    },
    {
      "id": "europe",
      "name": "Italy-Bund 10Y Spread",
      "score": 0.0,
      "value": "81 bp",
      "source": "OECD via FRED",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-08-01",
      "weight": 6,
      "source_url": "https://fred.stlouisfed.org/graph/?g=j3d3",
      "note": "Monthly automatic series uses level/deviation/velocity. A daily manual override uses the absolute anchor only.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 10.2,
        "robust_z": -0.98,
        "delta_5": -0.4325,
        "delta_20": 1.336,
        "velocity_pct_5": 59.3,
        "velocity_pct_20": 64.4
      },
      "quality": {}
    },
    {
      "id": "energy",
      "name": "Energy Shock",
      "score": 35.2,
      "value": "WTI $96.41 / Henry Hub $2.90",
      "source": "FRED DCOILWTICO + DHHNGSP",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-22",
      "weight": 7,
      "source_url": "https://fred.stlouisfed.org/series/DCOILWTICO",
      "note": "Uses the more stressed oil/gas signal; fast shocks matter even before absolute prices reach extreme thresholds.",
      "components": {
        "level": 0.0,
        "deviation": 65.1,
        "velocity": 62.9
      },
      "stats": {
        "oil_score": 35.2,
        "gas_score": 0.0
      },
      "quality": {}
    },
    {
      "id": "data_center",
      "name": "AI Data-center Financing",
      "score": 66.7,
      "value": "Event score",
      "source": "Reuters / deal evidence",
      "mode": "EVENT-DECAY",
      "as_of": "2026-09-18",
      "weight": 6,
      "source_url": "https://www.reuters.com/business/finance/oracles-18-billion-data-center-debt-under-pressure-ft-reports-2026-09-18/",
      "note": "Material repricing: $18bn of Project Jupiter loans were quoted around 89-91 cents and broader syndication reportedly stalled. Treat as sector stress, not yet a system-wide freeze.",
      "components": {
        "level": 66.7,
        "deviation": null,
        "velocity": null
      },
      "stats": {
        "raw_score_0_3": 2,
        "confidence": "high",
        "confidence_multiplier": 1.0,
        "age_days": 6,
        "freshness_multiplier": 1.0
      },
      "quality": {
        "confidence": "high"
      }
    },
    {
      "id": "private_credit",
      "name": "Private-credit Liquidity",
      "score": 66.7,
      "value": "Event score",
      "source": "Fund disclosures / optional BDC NAV discount",
      "mode": "EVENT/MARKET",
      "as_of": "2026-09-18",
      "weight": 8,
      "source_url": "https://www.reuters.com/markets/wealth/morgan-stanley-private-credit-fund-redemptions-remain-elevated-third-quarter-2026-09-18/",
      "note": "Morgan Stanley North Haven PIF saw 11.4% redemption requests versus a 5% repurchase limit. Elevated liquidity pressure, though the backlog may be stabilizing.",
      "components": {
        "level": 66.7,
        "deviation": null,
        "velocity": null
      },
      "stats": {
        "raw_score_0_3": 2,
        "confidence": "high",
        "confidence_multiplier": 1.0,
        "age_days": 6,
        "freshness_multiplier": 1.0,
        "bdc_discount_pct": null,
        "bdc_score": null
      },
      "quality": {
        "confidence": "high"
      }
    },
    {
      "id": "bank_ai",
      "name": "Bank AI-credit Inventory",
      "score": 56.7,
      "value": "Event score",
      "source": "Syndication / lender evidence",
      "mode": "EVENT-DECAY",
      "as_of": "2026-09-18",
      "weight": 5,
      "source_url": "https://www.reuters.com/business/finance/oracles-18-billion-data-center-debt-under-pressure-ft-reports-2026-09-18/",
      "note": "Banks reportedly retained more Oracle-linked project debt than planned after distribution weakened. This overlaps with the data-center event; v3 limits double counting through explicit channel weights and requires broad-market transmission for higher stages.",
      "components": {
        "level": 56.7,
        "deviation": null,
        "velocity": null
      },
      "stats": {
        "raw_score_0_3": 2,
        "confidence": "medium",
        "confidence_multiplier": 0.85,
        "age_days": 6,
        "freshness_multiplier": 1.0
      },
      "quality": {
        "confidence": "medium"
      }
    }
  ]
};
