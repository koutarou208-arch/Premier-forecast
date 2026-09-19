# Global Financial Crisis Watch v2

AI / Private Credit の局所ストレスが、広範な信用収縮・資金調達ストレスへ伝播しているかを監視する GitHub Pages ダッシュボードです。

## v2 changes

- 9 risk channels with explicit weights
- 4 pillars: Broad Credit / Funding & Liquidity / AI & Private Credit / Europe & Energy
- Stage 0-4 contagion ladder
- 365-day stress history
- automatic Treasury realized-volatility proxy
- automatic monthly Italy-Bund 10Y spread
- optional manual MOVE and daily Italy-Bund overrides
- source links and observation dates on each card
- structural event inputs for AI data-center lending, private-credit redemptions and bank loan inventory

## 9 risk channels and weights

| Channel | Weight | Main source |
| --- | ---: | --- |
| US IG Corporate OAS | 12% | FRED BAMLC0A0CM |
| US High Yield OAS | 18% | FRED BAMLH0A0HYM2 |
| St. Louis Financial Stress | 10% | FRED STLFSI4 |
| Treasury Vol / Liquidity | 10% | DGS10 realized vol + VIX; optional MOVE |
| Italy-Bund 10Y spread | 10% | OECD/FRED monthly; optional daily override |
| Energy shock | 10% | WTI + Henry Hub |
| AI data-center financing | 10% | event evidence |
| Private-credit liquidity | 12% | fund disclosures / event evidence |
| Bank AI-credit inventory | 8% | syndication / lender evidence |

Total = 100%. Each channel is scored 0-3 and converted to a weighted 0-100 Systemic Stress Score.

- 0-24: NORMAL
- 25-44: WATCH
- 45-64: ELEVATED
- 65-79: HIGH
- 80-100: CRITICAL

The overall score is not a crash probability.

## Contagion ladder

- Stage 0 — CALM: no material sector-to-system transmission
- Stage 1 — SECTOR REPRICING: AI / Private Credit stress is material but localized
- Stage 2 — CREDIT TRANSMISSION: broad IG/HY credit repricing appears alongside sector stress
- Stage 3 — FUNDING STRESS: broad credit and liquidity/volatility are both stressed
- Stage 4 — SYSTEMIC / FREEZE: severe broad credit and funding-market stress coexist

The ladder is intentionally stricter than the headline score.

## Automatic data

`scripts/update_data.py` downloads public FRED CSV data without an API key.

- BAMLC0A0CM — US investment-grade corporate OAS
- BAMLH0A0HYM2 — US high-yield OAS
- STLFSI4 — St. Louis Fed Financial Stress Index
- VIXCLS — VIX
- DCOILWTICO — WTI spot oil
- DHHNGSP — Henry Hub natural gas
- DGS10 — US 10Y Treasury yield
- DGS2 — US 2Y Treasury yield
- IRLTLT01ITM156N — Italy 10Y benchmark yield, monthly
- IRLTLT01DEM156N — Germany 10Y benchmark yield, monthly

### MOVE-like proxy

When `move_index.value` is null in `data/manual.json`, v2 computes a 20-trading-day realized volatility proxy from daily 10Y Treasury yield changes and annualizes it in basis points.

This is not the ICE BofA MOVE Index. A current MOVE reading can be entered manually; the engine uses the more severe signal.

### Italy-Bund

The automatic spread uses common-date monthly OECD/FRED 10Y observations: Italy 10Y minus Germany 10Y. A current daily value can override it through `europe_daily_spread_bps` in `data/manual.json`.

## Structural event inputs

`data/manual.json` stores the three channels without robust free continuous public series:

- AI data-center financing
- private-credit liquidity / redemptions
- bank AI-credit inventory

Use 0 = normal, 1 = watch, 2 = material stress, 3 = severe / broad impairment. Each entry should include `as_of`, `note`, and `source_url`.

## History

Every successful refresh writes `data/latest.js`, `data/history.json`, and `data/history.js`. History is capped at 365 observations.

## Refresh

GitHub Actions runs on weekdays and can also be triggered manually:

**Actions -> Update crisis dashboard v2 -> Run workflow**

Local refresh:

```bash
python3 scripts/update_data.py
```

## GitHub Pages

Enable **Settings -> Pages -> Deploy from a branch -> main / root**.

Then open:

`https://koutarou208-arch.github.io/Premier-forecast/`

## Interpretation cautions

- This is a monitoring framework, not a forecast or investment recommendation.
- Event-scored structural channels require periodic human review.
- Italy-Bund automatic data are monthly unless overridden.
- Treasury realized volatility is a MOVE-like proxy, not implied volatility.
- One AI financing event may affect multiple channels; v2 limits overlap through explicit weights and requires broad credit/liquidity deterioration for higher contagion stages.
