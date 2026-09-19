window.__RISK_DATA__ = {
  "updated_at": "2026-09-19T12:00:00Z",
  "score": 16.7,
  "level": "NORMAL",
  "summary": "No broad credit-freeze signal in the seeded snapshot. Structural AI/private-credit channels remain on watch.",
  "indicators": [
    {"id":"ai_credit","name":"AI corporate credit proxy","score":0,"value":"0.78%","source":"FRED BAMLC0A0CM","mode":"AUTO","note":"Broad US IG OAS proxy; not AI-specific."},
    {"id":"data_center","name":"Data-center financing","score":1,"value":"Manual","source":"Deal / lender evidence","mode":"MANUAL","note":"Watch financing discounts, failed syndications and covenant tightening."},
    {"id":"private_credit","name":"Private-credit liquidity","score":1,"value":"Manual","source":"Fund disclosures / reporting","mode":"MANUAL","note":"Watch redemptions, gates, NAV write-downs and delayed marks."},
    {"id":"bank_ai","name":"Bank AI-credit inventory","score":1,"value":"Manual","source":"Bank / syndication evidence","mode":"MANUAL","note":"Watch underwritten-but-unsold loans and balance-sheet retention."},
    {"id":"hy","name":"US High Yield OAS","score":0,"value":"2.70%","source":"FRED BAMLH0A0HYM2","mode":"AUTO","note":"Broad speculative-grade credit stress."},
    {"id":"treasury","name":"Treasury liquidity / volatility proxy","score":0,"value":"STLFSI -0.85 / VIX 15.44","source":"FRED STLFSI4 + VIXCLS","mode":"AUTO","note":"Proxy only; does not directly measure Treasury bid-ask depth."},
    {"id":"europe","name":"Europe sovereign spread","score":0,"value":"140 bp","source":"Manual Italy-Bund style spread","mode":"MANUAL","note":"Placeholder until updated with a current chosen euro-area sovereign spread."},
    {"id":"energy","name":"Energy shock","score":1,"value":"WTI $100.30 / Henry Hub $2.97","source":"WTI market close + FRED DHHNGSP","mode":"AUTO","note":"Composite uses the more severe of oil and gas stress scores."}
  ]
};
