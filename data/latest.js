window.__RISK_DATA__ = {
  "version": 3,
  "updated_at": "2026-09-19T14:33:17.361313Z",
  "score": 24.6,
  "raw_score": 24.6,
  "synchronization_bonus": 0.0,
  "level": "NORMAL",
  "summary": "NORMAL: AI/private-credit stress remains mainly sectoral; broad credit contagion is not yet confirmed.",
  "coverage_pct": 100.0,
  "breadth": {
    "score": 16.7,
    "stressed": 1,
    "available": 6,
    "severe": 0
  },
  "transmission": {
    "stage": 1,
    "label": "SECTOR REPRICING",
    "note": "AI infrastructure/private-credit channels are stressed, but broad contagion is not confirmed."
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
      "score": 0.0
    },
    {
      "name": "Funding / Liquidity",
      "score": 0.0
    },
    {
      "name": "AI / Private Credit",
      "score": 63.4
    },
    {
      "name": "Europe / Energy",
      "score": 26.7
    }
  ],
  "weights": {
    "ig_credit": 12,
    "hy_credit": 18,
    "financial_stress": 10,
    "rates_liquidity": 10,
    "europe": 10,
    "energy": 10,
    "data_center": 10,
    "private_credit": 12,
    "bank_ai": 8
  },
  "methodology": {
    "auto_components": {
      "level_weight": 45,
      "deviation_weight": 30,
      "velocity_weight": 25
    },
    "lookback_observations": 1260,
    "missing_data_policy": "exclude_and_renormalize",
    "event_decay": "confidence multiplier plus age-based decay after 30 days"
  },
  "diagnostics": {
    "us10y": 4.94,
    "us2y": 4.67,
    "curve_2s10s_bps": 27.000000000000046,
    "vix": 15.44,
    "realized_10y_vol_bps": 66.65204225559872,
    "move_manual": null,
    "italy_bund_bps": 80.59799999999998,
    "wti": 107.02,
    "gas": 2.97
  },
  "data_failures": [],
  "indicators": [
    {
      "id": "ig_credit",
      "name": "US IG Corporate OAS",
      "score": 0.0,
      "value": "0.78%",
      "source": "FRED BAMLC0A0CM",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-17",
      "weight": 12,
      "source_url": "https://fred.stlouisfed.org/series/BAMLC0A0CM",
      "note": "45% absolute level + 30% deviation from ~5y history + 25% 5/20-observation deterioration speed.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 17.8,
        "robust_z": -0.67,
        "delta_5": -0.02,
        "delta_20": -0.04,
        "velocity_pct_5": 33.7,
        "velocity_pct_20": 36.9
      },
      "quality": {}
    },
    {
      "id": "hy_credit",
      "name": "US High Yield OAS",
      "score": 0.0,
      "value": "2.70%",
      "source": "FRED BAMLH0A0HYM2",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-17",
      "weight": 18,
      "source_url": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
      "note": "Core contagion channel. Fast widening can score high even before the absolute OAS reaches crisis thresholds.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 11.2,
        "robust_z": -1.0,
        "delta_5": 0.0,
        "delta_20": -0.05,
        "velocity_pct_5": 57.7,
        "velocity_pct_20": 53.0
      },
      "quality": {}
    },
    {
      "id": "financial_stress",
      "name": "St. Louis Financial Stress",
      "score": 0.0,
      "value": "-0.85",
      "source": "FRED STLFSI4",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-11",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/series/STLFSI4",
      "note": "Cross-market stress measured against both fixed anchors and its own recent distribution.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 7.0,
        "robust_z": -0.95,
        "delta_5": -0.0794,
        "delta_20": -0.1764,
        "velocity_pct_5": 43.1,
        "velocity_pct_20": 41.4
      },
      "quality": {}
    },
    {
      "id": "rates_liquidity",
      "name": "Treasury Vol / Liquidity",
      "score": 0.0,
      "value": "RV20 66.65 bp / VIX 15.44",
      "source": "FRED DGS10 + VIXCLS",
      "mode": "AUTO/HYBRID",
      "as_of": "2026-09-17",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/series/DGS10",
      "note": "Uses the strongest signal from 10Y realized yield volatility, VIX, and optional MOVE. Missing inputs are not treated as zero.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "rv": 66.65204225559872,
        "move": null,
        "vix": 15.44
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
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/graph/?g=j3d3",
      "note": "Monthly automatic series uses level/deviation/velocity. A daily manual override uses the absolute anchor only.",
      "components": {
        "level": 0.0,
        "deviation": 0.0,
        "velocity": 0.0
      },
      "stats": {
        "percentile": 32.7,
        "robust_z": -0.39,
        "delta_5": -0.4325,
        "delta_20": 1.336,
        "velocity_pct_5": 51.2,
        "velocity_pct_20": 59.7
      },
      "quality": {}
    },
    {
      "id": "energy",
      "name": "Energy Shock",
      "score": 53.4,
      "value": "WTI $107.02 / Henry Hub $2.97",
      "source": "FRED DCOILWTICO + DHHNGSP",
      "mode": "AUTO-DYNAMIC",
      "as_of": "2026-09-15",
      "weight": 10,
      "source_url": "https://fred.stlouisfed.org/series/DCOILWTICO",
      "note": "Uses the more stressed oil/gas signal; fast shocks matter even before absolute prices reach extreme thresholds.",
      "components": {
        "level": 7.8,
        "deviation": 86.6,
        "velocity": 95.8
      },
      "stats": {
        "oil_score": 53.4,
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
      "weight": 10,
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
        "age_days": 1,
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
      "source": "Fund disclosures / Reuters",
      "mode": "EVENT-DECAY",
      "as_of": "2026-09-18",
      "weight": 12,
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
        "age_days": 1,
        "freshness_multiplier": 1.0
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
      "weight": 8,
      "source_url": "https://www.reuters.com/business/finance/oracles-18-billion-data-center-debt-under-pressure-ft-reports-2026-09-18/",
      "note": "Banks reportedly retained more Oracle-linked project debt than planned after distribution weakened. This overlaps with the data-center event, so v2 caps its portfolio weight.",
      "components": {
        "level": 56.7,
        "deviation": null,
        "velocity": null
      },
      "stats": {
        "raw_score_0_3": 2,
        "confidence": "medium",
        "confidence_multiplier": 0.85,
        "age_days": 1,
        "freshness_multiplier": 1.0
      },
      "quality": {
        "confidence": "medium"
      }
    }
  ]
};
