# Global Financial Crisis Watch v6

世界的な信用収縮を、**決定論的ストレスモデル + ニューラルネットEarly-Warningモデル**の二重系で監視する GitHub Pages ダッシュボードです。

v6では、v5までの12チャネル・5 Pillars・walk-forward backtestを残したまま、過去の市場ストレスパターンから学習する小型MLP ensembleを追加しています。

## v6 neural architecture

NNはルールモデルを置き換えません。役割は「今の市場パターンが、過去の危機窓の直前〜危機中にどれだけ似ているか」を別系統で評価することです。

- Input: 9 market channels
- Additional inputs: Breadth / Raw Market Score / Coverage
- Missingness flags: 9
- Total input features: 21
- Hidden layer 1: 12 units
- Hidden layer 2: 6 units
- Output: 1 sigmoid unit
- Ensemble: 5 independent seeds
- Activation: tanh / tanh / sigmoid
- L2 regularization + early stopping
- Positive-class weighting for class imbalance

Architecture:

```
21 inputs
   ↓
12 tanh
   ↓
 6 tanh
   ↓
 1 sigmoid
   ↓
Neural Early-Warning Score
```

## What the NN learns

Target = 1 when an observation is:

- inside one of the labeled stress windows, or
- within 60 calendar days before the stress window begins

Target = 0 otherwise.

The output is therefore an **Early-Warning similarity score**, not a literal probability that a financial crisis will occur.

## Temporal split

Random train/test split is not used.

- Train: through 2019-12-31
- Validation: 2020-01-01 through 2022-12-31
- Test / holdout: 2023-01-01 onward

This means the 2023 US regional-bank episode is not used to fit the model.

The validation period chooses the alert threshold and controls early stopping. The 2023+ period is held out for final evaluation.

## Hybrid score

v6 keeps three different quantities separate.

- **Systemic Stress Score** — existing 12-channel production score including AI / Private Credit event inputs
- **Market-only Score** — current public-market / funding / banking layer
- **Neural Early-Warning Score** — NN output

The optional Hybrid Market score is:

```
Hybrid Market = 65% × Rule Market Score + 35% × Neural Score
```

The deterministic Stage 0-4 remains authoritative. The NN is **not allowed to promote the system into Stage 2/3/4 by itself**.

## Ensemble uncertainty

The same architecture is trained five times with different deterministic seeds.

The dashboard reports:

- mean NN score
- standard deviation across the 5 models
- validation ROC AUC
- 2023+ holdout ROC AUC
- holdout Brier score
- holdout false-positive rate at the selected alert threshold

A large ensemble standard deviation means the neural prediction is unstable and should receive less confidence.

## Local sensitivity

For the current observation, v6 also measures how much the NN score changes when each input is neutralized one at a time.

This is displayed as **Local Sensitivity**.

It is useful for answering:

> Which current channel is pushing the neural score upward?

This is not causal attribution. It is a local model-sensitivity diagnostic.

## Historical validation

v5's walk-forward engine remains active.

- No future observations are used at each historical point
- 2007 onward
- Weekly baseline sampling
- Daily observations added around labeled stress windows
- Missing channels are excluded rather than treated as safe
- Historical Funding proxy follows the regime:
  - SOFR-IORB
  - SOFR-IOER
  - TED spread

## Historical credit-series limitation

FRED's ICE BofA OAS history available to this project is insufficient to reproduce the exact present-day production model back to 2008.

Therefore historical validation uses long-history public proxies:

- IG credit: BAA10Y
- broad credit: NFCICREDIT
- leveraged / risk: NFCIRISK

This means the historical-comparable model and current production model are intentionally shown as separate series.

## Current production channels

| Channel | Weight | Source / fallback |
| --- | ---: | --- |
| US IG Corporate OAS | 10% | BAMLC0A0CM |
| US High Yield OAS | 14% | BAMLH0A0HYM2 |
| Leveraged / Structured Credit | 10% | CCC OAS; optional CDX/CLO |
| St. Louis Financial Stress | 8% | STLFSI4 |
| Treasury Vol / Liquidity | 8% | DGS10 RV20 + VIX; optional MOVE |
| Repo / Funding Market | 10% | SOFR - IORB |
| Bank Short-term Funding | 8% | CPFF; optional Bank CDS |
| Italy-Bund | 6% | OECD/FRED; optional daily override |
| Energy shock | 7% | WTI + Henry Hub |
| AI Data-center Financing | 6% | event evidence |
| Private-credit Liquidity | 8% | event evidence; optional BDC NAV discount |
| Bank AI-credit Inventory | 5% | syndication / lender evidence |

## Dynamic rule score

Each automatic market channel is still scored using:

- Level 45%
- Deviation 30%
- Velocity 25%
- Breadth synchronization overlay

The neural model therefore learns from normalized channel stress states rather than raw market prices alone.

## Files

- `scripts/update_data.py` — production market scoring
- `scripts/backtest.py` — walk-forward historical validation
- `scripts/train_nn.py` — v6 neural ensemble training / holdout evaluation
- `data/latest.js` — current production snapshot
- `data/backtest.json` / `data/backtest.js` — historical validation
- `data/nn_model.json` / `data/nn_model.js` — NN model, metrics and current predictions
- `data/manual.json` — MOVE / CDX / CLO / Bank CDS / BDC overrides

## MCP search server

The repository now includes an official MCP Python SDK v2 server: `mcp_server.py`.

It exposes these tools:

- `get_current_state()` — latest Systemic / Market / Stage / NN state
- `get_indicator(name)` — fuzzy/alias lookup for one risk channel
- `search_crisis_data(query, limit)` — cross-search current indicators, pillars, backtest events, neural events and recent history
- `search_history(...)` — filter saved daily history by date / score / stage
- `get_backtest_event(name)` — retrieve one historical validation episode
- `get_neural_state(include_models=False)` — v6 neural ensemble diagnostics

Resources:

- `crisis://current`
- `crisis://history`
- `crisis://backtest`
- `crisis://neural`

### Install

```bash
python3 -m pip install -r requirements-mcp.txt
```

The project pins the official Python SDK to MCP v2:

```
mcp[cli]>=2,<3
```

### Local stdio mode

Default:

```bash
python3 mcp_server.py
```

Use `mcp.example.json` as a client configuration template. Replace the absolute path with the path to this repository.

Example client entry:

```json
{
  "mcpServers": {
    "global-financial-crisis-watch": {
      "command": "python3",
      "args": ["/ABSOLUTE/PATH/TO/Premier-forecast/mcp_server.py"],
      "env": {
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

### MCP Inspector

```bash
mcp dev mcp_server.py
```

### Streamable HTTP

For a local HTTP endpoint:

```bash
MCP_TRANSPORT=streamable-http MCP_HOST=127.0.0.1 MCP_PORT=8000 python3 mcp_server.py
```

Connect the MCP client to:

```
http://127.0.0.1:8000/mcp
```

The HTTP transport should be deployed behind proper authentication and transport-security configuration before exposure to the public internet.

### Search examples

Ask the MCP client to:

- 「現在の金融危機スコアを取得」
- 「repo市場の指標を検索」
- 「銀行ストレスを検索」
- 「Private Creditに関係するデータを検索」
- 「Stage 2以上の履歴を検索」
- 「2008年金融危機のバックテスト結果を取得」
- 「現在のNNスコアとholdout AUCを取得」

The search layer includes Japanese/English aliases for common concepts such as Repo, Banking, AI/Data Center, Private Credit, Credit, Energy and Europe.

## GitHub Actions

Run manually:

**Actions -> Update crisis dashboard v6 -> Run workflow**

Pipeline:

1. Install NumPy
2. Validate Python syntax
3. Refresh production market data
4. Run walk-forward backtest
5. Train 5-model MLP ensemble
6. Validate current / backtest / NN payloads
7. Commit generated snapshot, history, backtest and NN model

## GitHub Pages

https://koutarou208-arch.github.io/Premier-forecast/

## Important

The NN score is **not a calibrated crisis probability**.

There are only a small number of independent historical crisis episodes, and observations inside one crisis are serially correlated. A high AUC on a holdout period does not prove that the model will correctly predict the next crisis.

For that reason v6 is deliberately hybrid:

**deterministic rules for system state + neural network for nonlinear early-warning pattern detection.**
