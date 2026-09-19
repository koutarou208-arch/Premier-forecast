window.__RISK_DATA__ = {
  "version": 2,
  "updated_at": "2026-09-19T14:20:00Z",
  "score": 23.3,
  "level": "NORMAL",
  "summary": "NORMAL: AI infrastructure/private-credit stress is material, but broad market contagion is not yet confirmed.",
  "transmission": {
    "stage": 1,
    "label": "SECTOR REPRICING",
    "note": "AI infrastructure/private-credit channels show stress, but broad credit transmission is not confirmed."
  },
  "flags": [
    {"type":"AI_CREDIT","label":"AI / Private Credit stress is material"}
  ],
  "pillars": [
    {"name":"Broad Credit","score":0.0},
    {"name":"Funding / Liquidity","score":0.0},
    {"name":"AI / Private Credit","score":66.7},
    {"name":"Europe / Energy","score":16.7}
  ],
  "diagnostics": {
    "us10y": 5.01,
    "us2y": 4.74,
    "curve_2s10s_bps": 27.0,
    "vix": 15.44,
    "realized_10y_vol_bps": null,
    "move_manual": null,
    "italy_bund_bps": 80.598,
    "italy_bund_frequency": "monthly",
    "wti": 100.30,
    "gas": 2.97
  },
  "data_failures": [],
  "indicators": [
    {"id":"ig_credit","name":"US IG Corporate OAS","score":0,"value":"0.78%","source":"FRED BAMLC0A0CM","mode":"AUTO","as_of":"2026-09-17","weight":12,"source_url":"https://fred.stlouisfed.org/series/BAMLC0A0CM","note":"Broad investment-grade spread. AI-specific stress should eventually appear here if contagion broadens."},
    {"id":"hy_credit","name":"US High Yield OAS","score":0,"value":"2.70%","source":"FRED BAMLH0A0HYM2","mode":"AUTO","as_of":"2026-09-17","weight":18,"source_url":"https://fred.stlouisfed.org/series/BAMLH0A0HYM2","note":"Core contagion indicator. A sustained move through 6-9% OAS would be materially different from an equity-only correction."},
    {"id":"financial_stress","name":"St. Louis Financial Stress","score":0,"value":"-0.85","source":"FRED STLFSI4","mode":"AUTO","as_of":"2026-09-11","weight":10,"source_url":"https://fred.stlouisfed.org/series/STLFSI4","note":"Cross-market financial stress proxy. Positive and rising values signal stress above normal conditions."},
    {"id":"rates_liquidity","name":"Treasury Vol / Liquidity","score":0,"value":"RV20 pending / VIX 15.44","source":"FRED DGS10 + VIXCLS","mode":"AUTO","as_of":"2026-09-16","weight":10,"source_url":"https://fred.stlouisfed.org/series/DGS10","note":"RV20 is annualized 20-day realized volatility of daily 10Y Treasury yield changes. It is a MOVE-like proxy, not the MOVE index itself."},
    {"id":"europe","name":"Italy-Bund 10Y Spread","score":0,"value":"81 bp","source":"OECD via FRED","mode":"AUTO-MONTHLY","as_of":"2026-08-01","weight":10,"source_url":"https://fred.stlouisfed.org/graph/?g=j3d3","note":"Exact Italy minus Germany 10Y benchmark spread using common-date OECD/FRED observations. Monthly unless manually overridden with a current daily spread."},
    {"id":"energy","name":"Energy Shock","score":1,"value":"WTI $100.30 / Henry Hub $2.97","source":"FRED DCOILWTICO + DHHNGSP","mode":"AUTO","as_of":"2026-09-17","weight":10,"source_url":"https://fred.stlouisfed.org/series/DCOILWTICO","note":"Uses the more severe oil/gas stress score. High energy stress can limit the ability of central banks to cushion a credit shock."},
    {"id":"data_center","name":"AI Data-center Financing","score":2,"value":"Event score","source":"Reuters / deal evidence","mode":"EVENT","as_of":"2026-09-18","weight":10,"source_url":"https://www.reuters.com/business/finance/oracles-18-billion-data-center-debt-under-pressure-ft-reports-2026-09-18/","note":"Material repricing: $18bn of Project Jupiter loans were quoted around 89-91 cents and broader syndication reportedly stalled. Treat as sector stress, not yet a system-wide freeze."},
    {"id":"private_credit","name":"Private-credit Liquidity","score":2,"value":"Event score","source":"Fund disclosures / Reuters","mode":"EVENT","as_of":"2026-09-18","weight":12,"source_url":"https://www.reuters.com/markets/wealth/morgan-stanley-private-credit-fund-redemptions-remain-elevated-third-quarter-2026-09-18/","note":"Morgan Stanley North Haven PIF saw 11.4% redemption requests versus a 5% repurchase limit. Elevated liquidity pressure, though the backlog may be stabilizing."},
    {"id":"bank_ai","name":"Bank AI-credit Inventory","score":2,"value":"Event score","source":"Syndication / lender evidence","mode":"EVENT","as_of":"2026-09-18","weight":8,"source_url":"https://www.reuters.com/business/finance/oracles-18-billion-data-center-debt-under-pressure-ft-reports-2026-09-18/","note":"Banks reportedly retained more Oracle-linked project debt than planned after distribution weakened. This overlaps with the data-center event, so v2 caps its portfolio weight."}
  ]
};
