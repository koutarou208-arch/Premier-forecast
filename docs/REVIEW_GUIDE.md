# Implementation Review Guide

This document is the acceptance checklist for Global Financial Crisis Watch.

Use it instead of reviewing every line of code.

---

# 1. Review result summary

Current implementation status:

- Market ingestion: operational
- Rule scoring: operational
- Walk-forward backtest: operational
- Neural ensemble: operational, but threshold calibration remains weak
- Self-improvement agent: operational with guardrails
- News collection: operational
- Vector search: operational
- Hybrid news retrieval: operational
- News time series: operational
- Knowledge graph materialization: operational
- MCP integration: operational
- Dashboard: operational

The system is technically functional, but there are several architecture/model-quality items that should be treated as open review findings.

---

# 2. Severity definitions

- **P0** — system can produce materially incorrect behavior or unsafe automation
- **P1** — important model/reliability problem; should be fixed before calling the system production-grade
- **P2** — architecture/maintainability problem
- **P3** — cleanup/usability improvement

---

# 3. Current review findings

## P1 — NN operational threshold does not generalize to holdout

Current selected NN threshold: 72.

Validation:

- recall: about 60.6%
- false-positive rate: about 4.3%

2023+ holdout:

- recall: 0%
- false-positive rate: 0%

Interpretation:

The NN has useful ranking signal, but the selected operational threshold does not detect the holdout positives.

Acceptance requirement:

- use event-level / rolling-origin threshold validation
- do not claim the NN alert threshold is production-calibrated until holdout/event-level detection improves

---

## P1 — Self-improvement calibration can overfit its own calibration period

The agent chooses candidates and an alert threshold using pre-2023 calibration observations.

This is safer than tuning on the 2023+ holdout, but the candidate evaluation still reuses the same historical regimes repeatedly.

Current accepted change:

- Rule 65% → 60%
- NN 35% → 40%

Calibration objective improved.

However, post-change holdout objective was slightly worse than the incumbent.

This does not mean the change is necessarily wrong; it means calibration improvement is not evidence of generalization.

Acceptance requirement:

- use event-level cross-validation / leave-one-event-out evaluation for agent candidate selection
- treat holdout only as monitoring, as already implemented

---

## P1 — NN local sensitivity has an out-of-distribution explanation artifact

Current largest sensitivity is `coverage_pct`.

The explanation method sets each feature to zero.

For coverage, zero means an unrealistic state and is outside the normal operating distribution.

Therefore the result can be misleading.

Acceptance requirement:

Replace zeroing with one of:

- normal-period median baseline
- Integrated Gradients
- permutation against realistic historical values

---

## P1 — News event clustering is currently weak

Latest state:

- retained articles: roughly 595
- event clusters: roughly 517

Most articles therefore remain separate events.

The intended purpose of clustering is to prevent syndicated coverage of one event from being counted as many independent events.

Acceptance requirement:

Measure:

```text
cluster compression ratio
duplicate publisher ratio
same-event recall
false merge rate
```

and tune clustering on a labeled sample.

---

## P1 — News-source trust is too coarse

Official Fed/ECB/BIS sources have high trust.

Google News RSS results currently inherit a generic trust value rather than publisher-specific quality.

Therefore Reuters, a low-quality blog and another publisher can receive the same initial trust weight.

Acceptance requirement:

Add publisher-level source quality and preserve the difference between:

- official primary source
- major wire / financial press
- specialist publication
- unknown / low-confidence publisher

Do not use publisher reputation as truth; use it only as a retrieval-quality prior.

---

## P1 — Schedule bug in market update workflow

Current cron:

```
30 23 * * 1-5
```

GitHub cron is UTC.

This corresponds to Tuesday–Saturday 08:30 JST, not Monday–Friday 08:30 JST.

If intended schedule is Monday–Friday 08:30 JST, it should be:

```
30 23 * * 0-4
```

---

## P2 — Vector DB durability should be described precisely

The portable durable store is:

`data/news_corpus.jsonl`

The SQLite + sqlite-vec database is rebuilt from that corpus when absent.

Therefore the design is:

> durable corpus + reproducible vector index

not:

> permanently committed vector database

This is technically reasonable, but documentation and user-facing explanations must use the correct wording.

---

## P2 — Graph DB is materialized but MCP graph retrieval mostly uses snapshot data

LadybugDB is created and validated.

However, MCP graph traversal/search currently works mainly from:

`data/graph_snapshot.json`

plus vector-search seeds.

This means LadybugDB is not yet the primary online query path.

Acceptance options:

1. Keep current architecture and describe Ladybug as a materialized/validated graph store.
2. Or move graph traversal/search to direct Ladybug Cypher queries.

---

## P2 — Large generated files are committed frequently

Current generated files include approximately:

- graph snapshot: ~1.8 MB
- news corpus: ~0.65 MB
- news time series: ~0.64 MB
- backtest: ~1 MB

News intelligence can update every two hours.

Even though binary DB files are excluded, repeatedly committing large generated JSON snapshots can make Git history grow quickly.

Acceptance requirement:

Choose one:

- commit daily snapshots only
- store frequent outputs as Actions artifacts/caches
- keep only compact deltas
- move generated intelligence state to a dedicated data branch/release/storage layer

---

## P2 — Several modules have too many responsibilities

Current large files:

- `mcp_server.py` ~33 KB
- `scripts/update_data.py` ~33 KB
- `scripts/news_intelligence.py` ~23 KB

This is difficult for a beginner and increases regression risk.

Recommended target structure:

```text
src/
  market/
    fetch.py
    scoring.py
    schemas.py

  model/
    backtest.py
    neural.py
    evaluation.py

  news/
    collect.py
    classify.py
    cluster.py
    timeseries.py

  retrieval/
    vector_store.py
    hybrid_search.py

  graph/
    build.py
    query.py

  agent/
    optimizer.py
    guardrails.py

  mcp/
    tools_market.py
    tools_news.py
    tools_graph.py
    server.py
```

The goal is not more files for their own sake.

The goal is:

> one module = one responsibility

---

## P2 — Tests are mainly smoke/integration tests, not unit tests

Existing CI successfully validates major pipelines.

That is good.

But a future change can still silently alter:

- score math
- RRF behavior
- event clustering
- graph edges
- candidate acceptance

Recommended test layers:

### Unit tests

Test one function with fixed inputs.

Examples:

- risk threshold calculation
- RRF ranking
- event clustering
- date parsing
- self-improvement guardrails

### Contract/schema tests

Validate generated JSON structure.

### Golden/regression tests

Use a fixed small dataset and assert known outputs.

### Integration tests

Already present.

---

## P2 — Dependency/model reproducibility needs stronger pinning

Dependencies use version ranges.

FastEmbed currently emits a warning that model pooling behavior changed between library versions.

Embedding changes can alter:

- topic classification
- event clustering
- vector ranking

without any source-code change.

Acceptance requirement:

Pin:

- FastEmbed version
- sqlite-vec version
- LadybugDB version
- NumPy version where relevant

Also record:

- embedding model name
- embedding dimension
- model/library version
- index build version

in generated metadata.

---

# 4. Review checklist for each pull request / change

You do not need to read all code.

Ask the implementer to provide this table.

| Question | Required answer |
|---|---|
| What changed? | One-sentence behavior change |
| Why? | Problem being solved |
| Inputs affected? | Exact files/APIs/data |
| Outputs affected? | Exact files/fields |
| Model logic affected? | Yes/No |
| Backtest changed? | Yes/No + before/after |
| Holdout touched? | Yes/No |
| News/vector/graph schema changed? | Yes/No |
| Test added? | Test name |
| CI result? | Pass/Fail |
| Rollback method? | Commit/config to revert |
| Cost impact? | 0 / changed |
| Main risk? | One concrete failure mode |

Do not approve a model change if this table is incomplete.

---

# 5. Acceptance checklist — market model

Approve only if:

- [ ] all required market channels are present or missingness is explicit
- [ ] score remains in 0–100
- [ ] no future data is used in backtest
- [ ] proxy series are disclosed
- [ ] Stage logic is unchanged or separately reviewed
- [ ] current output is reproducible

---

# 6. Acceptance checklist — neural model

Approve only if:

- [ ] train / validation / holdout split is explicit
- [ ] threshold selection uses no holdout data
- [ ] AUC is not described as accuracy/probability
- [ ] event-level behavior is shown
- [ ] uncertainty is reported
- [ ] explanation method is not obviously out-of-distribution

---

# 7. Acceptance checklist — self-improvement agent

Approve only if:

- [ ] allowed fields are explicitly enumerated
- [ ] code rewrite remains disabled
- [ ] label/window rewrite remains disabled
- [ ] one-cycle change is bounded
- [ ] holdout is not used for candidate selection
- [ ] every accepted change has before/after metrics
- [ ] rollback is possible by restoring model_config.json

---

# 8. Acceptance checklist — news intelligence

Approve only if:

- [ ] source list is visible
- [ ] source failure does not break whole pipeline
- [ ] deduplication is measured
- [ ] article/event ratio is monitored
- [ ] publisher/source quality is visible
- [ ] full copyrighted article bodies are not mirrored
- [ ] published_at is retained
- [ ] each article maps to topics/indicators/entities

---

# 9. Acceptance checklist — vector/hybrid search

Approve only if:

- [ ] keyword search works without embeddings
- [ ] semantic search works in Japanese and English
- [ ] query returns source URL/publisher/time
- [ ] ranking method is documented
- [ ] hybrid result can explain lexical/vector contribution
- [ ] index can be rebuilt from durable corpus

---

# 10. Acceptance checklist — knowledge graph

Approve only if:

- [ ] node/edge schema is documented
- [ ] Article → Event exists
- [ ] Event → Topic exists
- [ ] Event → Indicator exists
- [ ] historical episodes exist
- [ ] PRECEDES edges use real timestamps
- [ ] graph can be rebuilt deterministically
- [ ] query path (snapshot vs Ladybug) is explicitly documented

---

# 11. Acceptance checklist — geopolitical / hybrid-threat intelligence

Approve only if:

- [ ] actor mention is stored separately from reported attribution
- [ ] suspected / disputed attribution is not rewritten as confirmed responsibility
- [ ] the event has a timestamp and source
- [ ] physical attack, infrastructure target, military response and explicit threat are separate dimensions
- [ ] duplicate reporting is clustered at event level
- [ ] campaign threads use reported-attribution evidence, not mere co-mention
- [ ] market-transmission links are labeled as hypotheses/candidates
- [ ] Geopolitical Escalation Index is described as a state index, not war probability
- [ ] geopolitical text cannot directly change Stage 0-4 or the financial-crisis score
- [ ] a synthetic unit test checks attribution handling

---
# 12. Acceptance checklist — automation

Approve only if:

- [ ] schedule timezone has been converted correctly
- [ ] workflows can be manually run
- [ ] CI validates generated data
- [ ] concurrent pushes are handled
- [ ] external-source failures are visible
- [ ] generated data does not trigger infinite workflow loops

---

# 13. What you should ask when someone explains this system

You can use these exact questions in a meeting:

1. **この変更で、入力と出力は何が変わりますか？**
2. **失敗すると、ユーザーにはどう見えますか？**
3. **過去データで改善しただけではなく、未使用データでも確認していますか？**
4. **この数字は確率ですか、スコアですか？**
5. **ニュースの同じ事件を二重カウントしていませんか？**
6. **Vector検索とキーワード検索はどう使い分けていますか？**
7. **Graph DBを本当に問い合わせていますか、それともJSONを読んでいますか？**
8. **この変更を元に戻すには何を戻せばいいですか？**
9. **テストで何を保証していて、何は保証していませんか？**
10. **この機能が壊れても金融危機スコア本体は壊れませんか？**

If the implementer cannot answer these clearly, the deliverable is not review-ready.

---

# 14. Current architecture verdict

The implementation is a strong prototype / research system.

It already has:

- automation
- holdout separation
- guardrails
- vector retrieval
- graph materialization
- integration tests
- reproducible generated state

It is not yet a clean production architecture because:

- model validation is still sparse-event constrained
- operational NN calibration is weak
- event clustering quality is not measured
- large generated state is committed frequently
- several modules are too large
- graph runtime and graph query path are not fully aligned

The next architectural milestone should therefore be:

> **make the system easier to verify before adding more features.**
