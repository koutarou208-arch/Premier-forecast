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
Hybrid Market = active_model_config.rule_weight × Rule Market Score
              + active_model_config.nn_weight × Neural Score

Current agent-tuned mix: 60% Rule / 40% Neural
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

## Guardrailed self-improvement agent

The repository includes an autonomous validation/improvement loop:

`scripts/self_improve_agent.py`

The agent does **not** rewrite Python code, crisis labels, or historical validation windows. It can only make small bounded changes to:

- market-channel weights
- Rule/NN hybrid mixing ratio

Cycle:

1. Observe the current backtest, NN ensemble and active model config.
2. Generate small candidate configurations.
3. Evaluate candidates using calibration data through 2022-12-31 only.
4. Check objective improvement, false-positive regression, event recall and event-peak regression.
5. Accept at most one candidate.
6. Save an audit record.
7. Push an accepted `data/model_config.json` change, which triggers a full production/backtest/NN recomputation.

### Holdout isolation

The 2023+ holdout is **report-only**.

It is explicitly excluded from candidate ranking and acceptance. The agent records holdout results after the decision so model drift remains visible without tuning directly to the holdout.

### Current guardrails

- one accepted change per cycle
- market weights move only 1 point at a time
- total market weight remains 81
- Hybrid NN share changes by at most 5 percentage points per cycle
- minimum calibration objective improvement required
- maximum allowed false-positive-rate deterioration
- minimum event recall
- maximum allowed regression in any calibration-event peak
- code rewrite disabled
- label rewrite disabled
- backtest-window rewrite disabled

### Schedule

`.github/workflows/self-improve-agent.yml` runs weekly at **Sunday 08:00 JST** and can also be launched manually.

Generated audit files:

- `data/model_config.json` — active model configuration
- `data/agent_policy.json` — immutable guardrail policy unless changed by a human
- `data/agent_state.json` / `data/agent_state.js` — latest cycle
- `data/agent_history.json` — accepted/rejected cycle history

The dashboard shows the latest decision, candidate count, objective change, calibration false-positive rate and accepted configuration change.

## News intelligence: vector DB + time series + knowledge graph

The system now maintains a separate news-intelligence layer for evidence retrieval and historical context.

### Sources

The collector uses free/public feeds only:

- Federal Reserve official RSS — all releases, monetary policy, credit/liquidity
- ECB official RSS — press/speeches/interviews and statistical releases
- BIS official media-release RSS
- Google News RSS queries covering systemic risk, repo/funding, banking, corporate credit, private credit, AI data-center financing, energy, Europe and Japan

The collector stores **headline, short RSS summary, URL, source/publisher and publication time**. It does not mirror complete article bodies.

### Durable corpus

Portable source of truth:

- `data/news_corpus.jsonl`

Retention is currently 365 days with a cap of 5,000 retained articles. Articles are deduplicated by normalized title/publisher/day.

Binary database files are intentionally excluded from Git history:

- `data/news.db`
- `data/knowledge_graph/`

They are deterministically rebuilt from the portable corpus and graph snapshot. This avoids committing a changed multi-megabyte binary every two hours.

### Persistent local vector database

`intelligence_store.py` builds an embedded SQLite database using:

- SQLite
- FTS5 for lexical/BM25 retrieval
- `sqlite-vec` for 384-dimensional vector retrieval
- FastEmbed / ONNX using multilingual MiniLM

Each news item is enriched with:

- topics
- linked crisis indicators
- entities
- event cluster
- relevance
- publisher/source trust
- publication time

### News hybrid retrieval

News retrieval combines:

```
FTS5 / BM25
      +
sqlite-vec semantic nearest neighbours
      ↓
Reciprocal Rank Fusion
      +
recency
      +
source trust
```

The MCP tool is:

```
search_news_intelligence(query, limit)
```

For a query spanning both market state and news evidence:

```
search_all_intelligence(query, limit)
```

This performs cross-domain RRF over the structured crisis model and news-vector results.

### Internal time series

Every ingestion cycle rebuilds:

- `data/news_timeseries.json`

Daily rows are stored separately for `topic` and `indicator`, including:

- article count
- distinct event count
- distinct publisher count
- average relevance
- maximum relevance

MCP:

```
get_news_timeseries(key, kind, start_date, end_date, days)
```

This makes the news layer usable as a future quantitative model feature instead of only transient text context.

### Event clustering

Semantically similar articles in the same risk topic and nearby time window are clustered into an event. This reduces a single widely syndicated story from appearing to be many independent events.

The event ID is attached to every article before vector/graph indexing.

### Knowledge graph

The graph layer uses **LadybugDB**, an actively developed embedded property-graph database and successor to KuzuDB.

Portable graph source:

- `data/graph_snapshot.json`

Runtime graph database:

- `data/knowledge_graph/`

Node kinds include:

- Article
- Event
- Entity
- Topic
- Indicator
- Source
- Day
- HistoricalEpisode

Relationship types include:

- `EVIDENCE_FOR`
- `MENTIONS`
- `PUBLISHED_BY`
- `ABOUT`
- `IMPACTS`
- `OBSERVED_ON`
- `PRECEDES`

Historical validation episodes — GFC, Euro sovereign stress, 2019 repo stress, COVID liquidity shock and 2023 regional banks — are inserted into the same graph and linked to the relevant topics/indicators.

Ladybug is bulk-loaded with `COPY FROM`; nodes/edges are not inserted one at a time.

MCP:

```
search_event_graph(query, limit)
get_event_neighborhood(event_id, hops, limit)
```

### Automated update

`.github/workflows/news-intelligence.yml` runs every two hours.

Pipeline:

1. Fetch feeds in parallel with per-source failure isolation
2. Deduplicate and retain the portable corpus
3. Multilingual embedding classification
4. Event clustering
5. Build topic/indicator daily time series
6. Build SQLite FTS5 + sqlite-vec vector DB
7. Build graph snapshot
8. Materialize LadybugDB graph
9. Test BM25/vector hybrid retrieval, Japanese retrieval, time series, graph and MCP integration
10. Commit only portable intelligence state

### Model-safety boundary

News evidence is **not yet allowed to directly promote Stage 0-4 or change the crisis score**.

The system is collecting the time series first so the news-derived features can later be evaluated out-of-sample. This prevents adding an unbacktested text signal merely because it looks convincing in the current news cycle.

## MCP search server

The repository now includes an official MCP Python SDK v2 server: `mcp_server.py`.

It exposes these tools:

- `get_current_state()` — latest Systemic / Market / Stage / NN state
- `get_indicator(name)` — fuzzy/alias lookup for one risk channel
- `search_crisis_data(query, limit, semantic=True)` — hybrid lexical + embedding search across current indicators, pillars, backtest events, neural events and recent history
- `semantic_search_crisis_data(query, limit)` — embedding-first multilingual semantic search
- `search_history(...)` — filter saved daily history by date / score / stage
- `get_backtest_event(name)` — retrieve one historical validation episode
- `get_neural_state(include_models=False)` — v6 neural ensemble diagnostics
- `get_self_improvement_state()` — latest agent decision, guardrails, candidates and active configuration
- `search_news_intelligence(query, limit)` — persistent BM25 + vector + RRF news search
- `search_all_intelligence(query, limit)` — cross-domain structured + news retrieval
- `get_news_timeseries(...)` — news-derived topic/indicator time series
- `search_event_graph(query, limit)` — semantic search over knowledge-graph nodes
- `get_event_neighborhood(event_id, hops, limit)` — graph traversal around an event

Resources:

- `crisis://current`
- `crisis://history`
- `crisis://backtest`
- `crisis://neural`
- `crisis://agent`
- `crisis://news/status`
- `crisis://news/timeseries`
- `crisis://graph`

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

### Multilingual embedding search

MCP search now supports a hybrid ranker:

```
final relevance
  = lexical / alias matching
  + multilingual embedding cosine similarity
```

The embedding model is:

```
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

It maps Japanese and English sentences into the same dense vector space, so semantically equivalent wording can match even when the literal keywords differ.

The model runs locally through **FastEmbed / ONNX**, so semantic search does not require an embedding API key.

Install the optional semantic-search dependency:

```bash
python3 -m pip install -r requirements-embeddings.txt
```

Then enable embeddings:

```bash
MCP_EMBEDDINGS=on python3 mcp_server.py
```

Environment variables:

- `MCP_EMBEDDINGS=on` — require semantic embedding search; startup/search fails if the model cannot load
- `MCP_EMBEDDINGS=auto` — default; use embeddings when installed, otherwise fall back to lexical/alias search
- `MCP_EMBEDDINGS=off` — disable embedding search
- `MCP_EMBEDDING_MODEL` — override the FastEmbed-supported model
- `FASTEMBED_CACHE_PATH` — persistent model-cache directory; default is `~/.cache/fastembed`

`search_crisis_data()` uses a default 45% lexical / 55% semantic hybrid score.

`semantic_search_crisis_data()` is embedding-first: 15% lexical / 85% semantic.

The candidate corpus includes current indicators, pillars, historical backtest episodes, neural diagnostics, self-improvement-agent state and the latest 90 saved history rows. Candidate embeddings are cached in memory and rebuilt only when the underlying corpus changes. Model artifacts are cached separately by FastEmbed.

If the optional embedding package is unavailable, the normal MCP server remains usable and automatically falls back to the existing deterministic lexical search.

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
