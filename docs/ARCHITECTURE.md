# Architecture — beginner-friendly implementation map

## 1. What this system is

Global Financial Crisis Watch is a financial-risk monitoring system with six major layers:

1. Market-data ingestion
2. Deterministic rule scoring
3. Historical backtesting
4. Neural early-warning model
5. News / vector / graph intelligence
6. MCP interface and dashboard

The important review principle is:

> Do not review Python line by line. Review the responsibility and output of each layer.

---

## 2. System map

```text
                  ┌────────────────────────────┐
                  │ Public market data / FRED  │
                  └──────────────┬─────────────┘
                                 │
                                 v
                       scripts/update_data.py
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
               v                                   v
       Rule / market score                   data/latest.js
               │
               v
        scripts/backtest.py
               │
               v
        data/backtest.json
               │
               v
         scripts/train_nn.py
               │
               v
         data/nn_model.json
               │
               ├───────────────┐
               │               │
               v               v
       Hybrid market score   Dashboard
               │
               v
  scripts/self_improve_agent.py
               │
               v
       data/model_config.json


 News / RSS / official sources
               │
               v
 scripts/news_intelligence.py
               │
      ┌────────┼──────────────┐
      │        │              │
      v        v              v
news_corpus  time series   graph_snapshot
 .jsonl       .json          .json
      │                        │
      v                        v
intelligence_store.py      LadybugDB
      │
      ├─ SQLite FTS5
      ├─ sqlite-vec
      ├─ BM25
      └─ vector search
               │
               v
          mcp_server.py
               │
    ┌──────────┼──────────┐
    v          v          v
 ChatGPT     Cursor      Claude etc.
```

---

## 3. Source code vs generated data

This distinction is critical during review.

### Human-controlled source code

These files define behavior:

- `scripts/update_data.py`
- `scripts/backtest.py`
- `scripts/train_nn.py`
- `scripts/self_improve_agent.py`
- `scripts/news_intelligence.py`
- `intelligence_store.py`
- `mcp_server.py`
- `app.js`
- `index.html`
- workflow YAML files under `.github/workflows/`

Changes here can change system behavior.

### Human-controlled configuration

These files define parameters/policy:

- `data/model_config.json`
- `data/agent_policy.json`
- `data/backtest_config.json`
- `data/news_sources.json`
- `data/news_taxonomy.json`
- `data/manual.json`

Changes here can alter outputs without changing Python code.

### Machine-generated state

These are outputs, not source logic:

- `data/latest.js`
- `data/history.json`
- `data/backtest.json`
- `data/nn_model.json`
- `data/agent_state.json`
- `data/agent_history.json`
- `data/news_corpus.jsonl`
- `data/news_timeseries.json`
- `data/graph_snapshot.json`
- `data/news_intelligence_status.json`

Review these for validity, not implementation style.

---

## 4. Responsibility of each important file

| File | Responsibility | What to review |
|---|---|---|
| `scripts/update_data.py` | Fetch market data and calculate current rule scores | Inputs, thresholds, missing-data behavior, score range |
| `scripts/backtest.py` | Reconstruct historical score without lookahead | Data proxies, event windows, future leakage |
| `scripts/train_nn.py` | Train MLP ensemble and calculate NN score | Train/validation/holdout split, calibration, overfit |
| `scripts/self_improve_agent.py` | Test small config changes and accept/reject | Guardrails, optimization leakage, allowed change scope |
| `scripts/news_intelligence.py` | Fetch/enrich/dedupe/cluster news and build time series/graph | Source quality, duplicates, event clustering |
| `intelligence_store.py` | Build/search FTS5 + vector database | Retrieval logic, vector rebuild behavior |
| `mcp_server.py` | Expose tools/resources to MCP clients | Tool behavior, error handling, security |
| `app.js` | Render dashboard | Correct display of generated data |
| workflows | Automation/CI | Scheduling, test coverage, generated-file commits |

---

## 5. Market-risk path

The production market path is:

```text
FRED/public data
  ↓
update_data.py
  ↓
12 risk channels
  ↓
weighted deterministic score
  ↓
Stage / current dashboard state
```

The deterministic layer remains authoritative for Stage 0–4.

The neural model does not independently promote the system to a severe stage.

---

## 6. Neural model path

```text
Historical backtest rows
  ↓
21 input features
  ↓
MLP: 21 → 12 → 6 → 1
  ↓
5-model ensemble
  ↓
Neural early-warning score
```

Temporal split:

- Train: through 2019
- Validation: 2020–2022
- Holdout: 2023+

Important:

> Neural score is not a calibrated probability of financial crisis.

---

## 7. Self-improvement path

```text
Current config
  ↓
Generate bounded candidates
  ↓
Evaluate on pre-2023 calibration data
  ↓
Guardrail checks
  ↓
Accept at most one change
  ↓
Update model_config.json
```

The agent is not allowed to:

- rewrite Python code
- rewrite event labels
- rewrite historical event windows
- use 2023+ holdout data for automatic candidate selection

---

## 8. News intelligence path

```text
RSS / Google News RSS
  ↓
deduplication
  ↓
multilingual embedding
  ↓
topic / entity / indicator mapping
  ↓
event clustering
  ↓
portable corpus
  ├─ vector search
  ├─ time series
  └─ knowledge graph
```

Persistent source of truth:

- `data/news_corpus.jsonl`

Runtime vector DB:

- `data/news.db`

Important implementation detail:

> The SQLite vector DB is rebuilt from the durable JSONL corpus when necessary. The binary DB itself is not committed to Git.

---

## 9. Hybrid news search

News retrieval uses:

```text
FTS5 / BM25 lexical search
        +
sqlite-vec semantic search
        ↓
Reciprocal Rank Fusion
        +
recency / trust
```

Cross-domain MCP retrieval additionally merges:

- structured market data
- backtest history
- neural diagnostics
- self-improvement state
- news-vector results

---

## 10. Knowledge graph

Graph concepts:

### Node types

- Article
- Event
- Entity
- Topic
- Indicator
- Source
- Day
- HistoricalEpisode

### Edge types

- EVIDENCE_FOR
- MENTIONS
- PUBLISHED_BY
- ABOUT
- IMPACTS
- OBSERVED_ON
- PRECEDES

Runtime graph engine:

- LadybugDB

Portable durable graph:

- `data/graph_snapshot.json`

Important implementation detail:

> The graph database is materialized and validated, but MCP retrieval currently relies primarily on the portable graph snapshot plus vector-search seeds rather than issuing all graph retrieval directly to LadybugDB.

---

## 11. Automation

### Market dashboard

`.github/workflows/update-dashboard.yml`

Runs market refresh, backtest, NN training, MCP smoke test, validation and commit.

### News intelligence

`.github/workflows/news-intelligence.yml`

Runs every two hours:

1. collect news
2. embed/classify
3. cluster events
4. generate time series
5. build vector DB
6. build graph
7. run integration tests
8. commit portable state

### Self-improvement

`.github/workflows/self-improve-agent.yml`

Runs weekly and evaluates bounded configuration changes.

---

## 12. The five things a non-programmer should review

For every feature, ask only these five questions:

1. **Input** — What information does it read?
2. **Logic** — What decision is it making?
3. **Output** — What file/value does it produce?
4. **Validation** — How do we know it worked?
5. **Failure mode** — What happens when input/data/model is wrong?

If those five answers are clear, the implementation is reviewable even without reading Python.
