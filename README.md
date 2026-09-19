# Global Financial Crisis Watch

世界的な信用収縮・金融ストレスの早期警戒ダッシュボードです。

## 8 indicators

1. AI corporate credit proxy — ICE BofA US Corporate OAS (FRED)
2. Data-center financing pressure — manual structural score
3. Private-credit liquidity / redemptions — manual structural score
4. Bank AI-credit inventory pressure — manual structural score
5. US High Yield OAS — FRED
6. Treasury liquidity / volatility proxy — STLFSI4 + VIX
7. Europe sovereign spread — manual Italy-Bund style spread input
8. Energy shock — WTI + Henry Hub natural gas

Each indicator is scored 0-3. The dashboard converts the equal-weight average into a 0-100 stress score.

- 0-24: NORMAL
- 25-44: WATCH
- 45-64: ELEVATED
- 65-79: HIGH
- 80-100: CRITICAL

This is a monitoring tool, not a forecast or investment recommendation.

## Automatic data

`scripts/update_data.py` downloads public CSV data from FRED with no API key required and generates `data/latest.js`.

Automatic series:

- `BAMLC0A0CM` — US investment-grade corporate OAS
- `BAMLH0A0HYM2` — US high-yield OAS
- `STLFSI4` — St. Louis Fed Financial Stress Index
- `VIXCLS` — VIX
- `DCOILWTICO` — WTI spot oil
- `DHHNGSP` — Henry Hub natural gas

## Manual structural inputs

Edit `data/manual.json` for indicators that do not have a clean, free, continuous public series:

- data-center financing pressure
- private-credit redemption/liquidity pressure
- bank AI-credit inventory pressure
- Europe sovereign spread

Manual scores use `0 = normal`, `1 = watch`, `2 = high`, `3 = severe`.

## Run locally

Open `index.html` in a browser. The dashboard reads `data/latest.js`, so it works without a local web server.

To refresh data:

```bash
python3 scripts/update_data.py
```

## GitHub Pages

In GitHub: **Settings -> Pages -> Deploy from a branch -> main / root**.

The included GitHub Actions workflow refreshes the data on weekdays and can also be run manually with **Actions -> Update crisis dashboard -> Run workflow**.

## Important interpretation notes

- Broad US IG OAS is only a proxy for AI-related corporate credit conditions.
- STLFSI4/VIX are market-stress proxies, not direct Treasury bid-ask liquidity measurements.
- Henry Hub is a US natural-gas benchmark and does not replace European TTF gas.
- Manual structural indicators should be updated from primary reporting or high-quality financial reporting.
