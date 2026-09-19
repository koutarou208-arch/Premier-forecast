#!/usr/bin/env python3
"""MCP search server for Global Financial Crisis Watch.

Compatible with the official MCP Python SDK v2.
Default transport: stdio
Optional transport: streamable-http
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import pathlib
import re
from datetime import date
from typing import Any

from mcp.server import MCPServer

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"

EMBEDDING_MODEL = os.getenv(
    "MCP_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
FASTEMBED_CACHE = os.getenv(
    "FASTEMBED_CACHE_PATH",
    str(pathlib.Path.home() / ".cache" / "fastembed"),
)
_EMBEDDER = None
_EMBEDDER_ERROR = None
_EMBED_CACHE = {"signature": None, "vectors": None}


mcp = MCPServer(
    "Global Financial Crisis Watch",
    instructions=(
        "Search and inspect the Global Financial Crisis Watch dashboard data. "
        "Use get_current_state for the latest system condition, search_crisis_data "
        "for cross-dataset search, get_indicator for one channel, search_history "
        "for historical snapshots, get_backtest_event for historical validation, "
        "and get_neural_state for v6 neural early-warning diagnostics. Use search_news_intelligence for BM25+vector news search, search_all_intelligence for cross-domain retrieval, get_news_timeseries for event history, and search_event_graph/get_event_neighborhood for graph retrieval. Hybrid search uses multilingual embeddings when installed. "
        "Do not interpret neural scores as calibrated crisis probabilities."
    ),
)

ALIASES = {
    "repo": ["funding_market", "sofr", "iorb", "ioer", "funding"],
    "資金": ["funding_market", "funding", "repo", "liquidity"],
    "流動性": ["funding_market", "rates_liquidity", "liquidity"],
    "銀行": ["banking_stress", "bank_ai", "bank", "cpff", "cds"],
    "bank": ["banking_stress", "bank_ai", "cpff", "cds"],
    "ai": ["data_center", "bank_ai", "private_credit"],
    "データセンター": ["data_center"],
    "private credit": ["private_credit", "bdc"],
    "プライベートクレジット": ["private_credit", "bdc"],
    "信用": ["ig_credit", "hy_credit", "leveraged_credit", "credit"],
    "hy": ["hy_credit", "leveraged_credit"],
    "ig": ["ig_credit"],
    "ccc": ["leveraged_credit"],
    "clo": ["leveraged_credit", "clo"],
    "cdx": ["leveraged_credit", "cdx"],
    "energy": ["energy", "wti", "gas"],
    "原油": ["energy", "wti"],
    "欧州": ["europe", "italy", "bund"],
    "europe": ["europe", "italy", "bund"],
    "nn": ["neural", "mlp", "neural network"],
    "ニューラル": ["neural", "mlp", "neural network"],
    "金融危機": ["systemic", "crisis", "stress"],
}

def _read_json(path: pathlib.Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _read_js_payload(path: pathlib.Path, variable: str, default: Any) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
        m = re.search(rf"window\.{re.escape(variable)}\s*=\s*(.*);\s*$", text, re.S)
        if not m:
            return default
        return json.loads(m.group(1))
    except Exception:
        return default

def load_current() -> dict[str, Any]:
    return _read_js_payload(DATA / "latest.js", "__RISK_DATA__", {})

def load_history() -> list[dict[str, Any]]:
    return _read_json(DATA / "history.json", [])

def load_backtest() -> dict[str, Any]:
    return _read_json(DATA / "backtest.json", {})

def load_neural() -> dict[str, Any]:
    return _read_json(DATA / "nn_model.json", {})

def load_agent() -> dict[str, Any]:
    return _read_json(DATA / "agent_state.json", {})

def load_news_status() -> dict[str, Any]:
    return _read_json(DATA / "news_intelligence_status.json", {})

def load_news_timeseries() -> list[dict[str, Any]]:
    return _read_json(DATA / "news_timeseries.json", [])

def load_graph_snapshot() -> dict[str, Any]:
    return _read_json(DATA / "graph_snapshot.json", {"nodes": [], "edges": [], "stats": {}})

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())

def _query_terms(query: str) -> list[str]:
    q = _normalize(query)
    terms = set(re.findall(r"[a-z0-9_./%-]+|[ぁ-んァ-ヶ一-龯ー]+", q))
    for alias, expansions in ALIASES.items():
        if alias in q:
            terms.update(_normalize(x) for x in expansions)
    return sorted(t for t in terms if t)

def _search_score(query: str, obj: Any) -> float:
    text = _normalize(json.dumps(obj, ensure_ascii=False, sort_keys=True))
    terms = _query_terms(query)
    if not terms:
        return 0.0
    score = 0.0
    q = _normalize(query)
    if q and q in text:
        score += 8.0
    for term in terms:
        if term in text:
            score += 2.0
            score += min(3.0, text.count(term) * 0.25)
    return score

def _embedding_mode() -> str:
    return _normalize(os.getenv("MCP_EMBEDDINGS", "auto"))

def _get_embedder():
    global _EMBEDDER, _EMBEDDER_ERROR
    mode = _embedding_mode()
    if mode in {"0", "false", "off", "disabled", "none"}:
        _EMBEDDER_ERROR = "disabled by MCP_EMBEDDINGS"
        return None
    if _EMBEDDER is not None:
        return _EMBEDDER
    if _EMBEDDER_ERROR is not None and mode != "on":
        return None
    try:
        from fastembed import TextEmbedding
        _EMBEDDER = TextEmbedding(model_name=EMBEDDING_MODEL, cache_dir=FASTEMBED_CACHE)
        _EMBEDDER_ERROR = None
        return _EMBEDDER
    except Exception as e:
        _EMBEDDER_ERROR = f"{type(e).__name__}: {e}"
        if mode == "on":
            raise
        return None

def _semantic_text(item: dict[str, Any]) -> str:
    title = str(item.get("title") or "")
    kind = str(item.get("type") or "")
    key = str(item.get("key") or "")
    data = item.get("data") or {}
    body = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return f"type: {kind}\nkey: {key}\ntitle: {title}\ndata: {body}"

def _build_search_candidates() -> list[dict[str, Any]]:
    current = load_current()
    backtest = load_backtest()
    neural = load_neural()
    history = load_history()
    candidates: list[dict[str, Any]] = []

    for x in current.get("indicators", []):
        candidates.append({
            "type": "indicator",
            "key": x.get("id"),
            "title": x.get("name"),
            "data": _indicator_summary(x),
        })
    for p in current.get("pillars", []):
        candidates.append({
            "type": "pillar",
            "key": p.get("name"),
            "title": p.get("name"),
            "data": p,
        })
    for ev in backtest.get("events", []):
        candidates.append({
            "type": "backtest_event",
            "key": ev.get("id"),
            "title": ev.get("name"),
            "data": ev,
        })
    nn_current = neural.get("current", {}) if neural else {}
    if nn_current:
        candidates.append({
            "type": "neural_current",
            "key": "neural_current",
            "title": "Neural Early Warning",
            "data": nn_current,
        })
    agent = load_agent()
    if agent:
        candidates.append({
            "type": "self_improvement_agent",
            "key": "agent_state",
            "title": "Self Improvement Agent",
            "data": agent,
        })
    for ev in neural.get("event_evaluation", []) if neural else []:
        candidates.append({
            "type": "neural_event",
            "key": ev.get("id"),
            "title": ev.get("name"),
            "data": ev,
        })
    for row in history[-90:]:
        candidates.append({
            "type": "history",
            "key": row.get("date"),
            "title": f"History {row.get('date')}",
            "data": row,
        })
    return candidates

def _semantic_scores(query: str, candidates: list[dict[str, Any]]) -> list[float] | None:
    model = _get_embedder()
    if model is None:
        return None

    texts = [_semantic_text(x) for x in candidates]
    signature = hashlib.sha256("\n\x1e\n".join(texts).encode("utf-8")).hexdigest()
    if _EMBED_CACHE["signature"] != signature or _EMBED_CACHE["vectors"] is None:
        import numpy as np
        vectors = np.asarray(list(model.embed(texts)), dtype=np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        _EMBED_CACHE["vectors"] = vectors / norms
        _EMBED_CACHE["signature"] = signature

    import numpy as np
    q = np.asarray(list(model.embed([query]))[0], dtype=np.float32)
    q_norm = float(np.linalg.norm(q))
    if q_norm > 0:
        q = q / q_norm
    sims = _EMBED_CACHE["vectors"] @ q
    return [float(x) for x in sims]

def _hybrid_rank(
    query: str,
    candidates: list[dict[str, Any]],
    semantic: bool = True,
    lexical_weight: float = 0.45,
    semantic_weight: float = 0.55,
) -> tuple[list[tuple[float, float, float | None, dict[str, Any]]], str]:
    lexical_weight = max(0.0, float(lexical_weight))
    semantic_weight = max(0.0, float(semantic_weight))
    total = lexical_weight + semantic_weight
    if total <= 0:
        lexical_weight, semantic_weight, total = 1.0, 0.0, 1.0
    lexical_weight /= total
    semantic_weight /= total

    semantic_scores = _semantic_scores(query, candidates) if semantic else None
    mode = "hybrid" if semantic_scores is not None else "lexical"
    ranked = []
    for i, item in enumerate(candidates):
        lexical_raw = _search_score(query, item)
        lexical_norm = min(1.0, lexical_raw / 12.0)
        semantic_raw = None if semantic_scores is None else semantic_scores[i]
        semantic_norm = 0.0 if semantic_raw is None else max(0.0, min(1.0, semantic_raw))
        final = lexical_norm if semantic_scores is None else (
            lexical_weight * lexical_norm + semantic_weight * semantic_norm
        )
        if final > 0:
            ranked.append((final, lexical_raw, semantic_raw, item))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return ranked, mode

def _indicator_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "score": item.get("score"),
        "value": item.get("value"),
        "mode": item.get("mode"),
        "as_of": item.get("as_of"),
        "weight": item.get("weight"),
        "components": item.get("components"),
        "stats": item.get("stats"),
        "note": item.get("note"),
        "source": item.get("source"),
        "source_url": item.get("source_url"),
    }

@mcp.tool()
def get_search_capabilities(probe_embeddings: bool = False) -> dict[str, Any]:
    """Report lexical and embedding-search availability.

    Set probe_embeddings=true to actually load the embedding model.
    """
    installed = importlib.util.find_spec("fastembed") is not None
    loaded = _EMBEDDER is not None
    if probe_embeddings and _embedding_mode() not in {"0", "false", "off", "disabled", "none"}:
        try:
            loaded = _get_embedder() is not None
        except Exception:
            loaded = False
    return {
        "lexical_search": True,
        "alias_search": True,
        "embedding_mode": _embedding_mode(),
        "embedding_package_installed": installed,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_model_loaded": loaded,
        "embedding_error": _EMBEDDER_ERROR,
        "hybrid_default_weights": {"lexical": 0.45, "semantic": 0.55},
        "semantic_first_weights": {"lexical": 0.15, "semantic": 0.85},
        "news_corpus_present": (DATA / "news_corpus.jsonl").exists(),
        "news_vector_dependencies_installed": (
            importlib.util.find_spec("sqlite_vec") is not None
            and importlib.util.find_spec("fastembed") is not None
        ),
        "graph_snapshot_present": (DATA / "graph_snapshot.json").exists(),
        "ladybug_installed": importlib.util.find_spec("ladybug") is not None,
    }

@mcp.tool()
def get_current_state() -> dict[str, Any]:
    """Return the latest systemic, market, transmission and neural state."""
    current = load_current()
    neural = load_neural()
    nn_current = neural.get("current", {}) if neural else {}
    return {
        "updated_at": current.get("updated_at"),
        "version": current.get("version"),
        "systemic_stress_score": current.get("score"),
        "level": current.get("level"),
        "market_score": current.get("market_score"),
        "coverage_pct": current.get("coverage_pct"),
        "market_coverage_pct": current.get("market_coverage_pct"),
        "breadth": current.get("breadth"),
        "transmission": current.get("transmission"),
        "pillars": current.get("pillars"),
        "flags": current.get("flags"),
        "summary": current.get("summary"),
        "neural": {
            "score": nn_current.get("production_nn_score"),
            "uncertainty_std": nn_current.get("production_uncertainty_std"),
            "hybrid_market_score": nn_current.get("hybrid_market_score"),
            "alert": nn_current.get("alert"),
            "alert_threshold": nn_current.get("threshold_score"),
        },
        "data_failures": current.get("data_failures", []),
    }

@mcp.tool()
def get_indicator(name: str) -> dict[str, Any]:
    """Find one current risk indicator by id, name, alias or substring."""
    current = load_current()
    indicators = current.get("indicators", [])
    if not indicators:
        return {"found": False, "error": "No indicator data available."}

    q = _normalize(name)
    exact = [
        x for x in indicators
        if q in {_normalize(x.get("id")), _normalize(x.get("name"))}
    ]
    if exact:
        return {"found": True, "indicator": _indicator_summary(exact[0])}

    ranked = sorted(
        ((_search_score(name, x), x) for x in indicators),
        key=lambda p: p[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] <= 0:
        candidates = [
            {
                "type": "indicator",
                "key": x.get("id"),
                "title": x.get("name"),
                "data": _indicator_summary(x),
            }
            for x in indicators
        ]
        semantic_scores = _semantic_scores(name, candidates)
        if semantic_scores is not None and semantic_scores:
            best_i = max(range(len(semantic_scores)), key=lambda i: semantic_scores[i])
            if semantic_scores[best_i] >= 0.30:
                return {
                    "found": True,
                    "query": name,
                    "match_mode": "embedding",
                    "semantic_similarity": round(semantic_scores[best_i], 4),
                    "indicator": candidates[best_i]["data"],
                }
        return {
            "found": False,
            "query": name,
            "available": [{"id": x.get("id"), "name": x.get("name")} for x in indicators],
        }
    return {
        "found": True,
        "query": name,
        "match_score": round(ranked[0][0], 2),
        "indicator": _indicator_summary(ranked[0][1]),
        "alternatives": [
            {"id": x.get("id"), "name": x.get("name"), "match_score": round(s, 2)}
            for s, x in ranked[1:4] if s > 0
        ],
    }

@mcp.tool()
def search_crisis_data(
    query: str,
    limit: int = 10,
    semantic: bool = True,
    lexical_weight: float = 0.45,
    semantic_weight: float = 0.55,
) -> dict[str, Any]:
    """Hybrid search across current, historical, neural and agent data.

    Uses exact/alias lexical matching plus multilingual sentence embeddings when
    the optional embedding dependency is installed. Falls back to lexical search
    without failing the MCP server.
    """
    limit = max(1, min(int(limit), 50))
    candidates = _build_search_candidates()
    ranked, mode = _hybrid_rank(
        query,
        candidates,
        semantic=semantic,
        lexical_weight=lexical_weight,
        semantic_weight=semantic_weight,
    )
    return {
        "query": query,
        "terms": _query_terms(query),
        "search_mode": mode,
        "embedding_model": EMBEDDING_MODEL if mode == "hybrid" else None,
        "embedding_error": _EMBEDDER_ERROR if mode != "hybrid" and semantic else None,
        "weights": {
            "lexical": lexical_weight,
            "semantic": semantic_weight if mode == "hybrid" else 0.0,
        },
        "count": min(len(ranked), limit),
        "results": [
            {
                **item,
                "match_score": round(final * 100.0, 2),
                "lexical_score": round(lexical_raw, 2),
                "semantic_similarity": None if semantic_raw is None else round(semantic_raw, 4),
            }
            for final, lexical_raw, semantic_raw, item in ranked[:limit]
        ],
    }

@mcp.tool()
def semantic_search_crisis_data(query: str, limit: int = 10) -> dict[str, Any]:
    """Embedding-first semantic search with Japanese/English multilingual matching."""
    return search_crisis_data(
        query=query,
        limit=limit,
        semantic=True,
        lexical_weight=0.15,
        semantic_weight=0.85,
    )

@mcp.tool()
def search_news_intelligence(query: str, limit: int = 10) -> dict[str, Any]:
    """Hybrid BM25 + vector + recency/trust search over collected news intelligence."""
    try:
        from intelligence_store import search_news
        return search_news(query, limit=limit)
    except Exception as e:
        return {
            "available": False,
            "error": f"{type(e).__name__}: {e}",
            "setup": "Install requirements-intelligence.txt to enable persistent news vector search.",
        }

@mcp.tool()
def search_all_intelligence(query: str, limit: int = 10) -> dict[str, Any]:
    """Search structured crisis state and the persistent news vector store together."""
    limit = max(1, min(int(limit), 30))
    structured = search_crisis_data(query=query, limit=limit)
    news = search_news_intelligence(query=query, limit=limit)

    merged = []
    for rank, item in enumerate(structured.get("results", []), start=1):
        merged.append({
            "domain": "structured",
            "rrf_score": round(1.0 / (60 + rank), 8),
            "rank": rank,
            "item": item,
        })
    if news.get("available", True):
        for rank, item in enumerate(news.get("results", []), start=1):
            merged.append({
                "domain": "news",
                "rrf_score": round(1.0 / (60 + rank), 8),
                "rank": rank,
                "item": item,
            })
    merged.sort(key=lambda x: x["rrf_score"], reverse=True)
    return {
        "query": query,
        "mode": "cross-domain RRF(structured hybrid search + news BM25/vector hybrid search)",
        "structured": structured,
        "news": news,
        "merged": merged[:limit],
    }

@mcp.tool()
def get_news_timeseries(
    key: str | None = None,
    kind: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    days: int = 90,
) -> dict[str, Any]:
    """Return internally stored news/event time-series by topic or indicator."""
    rows = load_news_timeseries()
    end = date.fromisoformat(end_date) if end_date else date.today()
    start = date.fromisoformat(start_date) if start_date else end - __import__("datetime").timedelta(days=max(1, int(days)))
    out = []
    for row in rows:
        try:
            d = date.fromisoformat(row.get("day", ""))
        except Exception:
            continue
        if d < start or d > end:
            continue
        if key is not None and _normalize(row.get("key")) != _normalize(key):
            continue
        if kind is not None and _normalize(row.get("kind")) != _normalize(kind):
            continue
        out.append(row)
    return {
        "filters": {"key": key, "kind": kind, "start_date": start.isoformat(), "end_date": end.isoformat()},
        "count": len(out),
        "results": out,
    }

@mcp.tool()
def search_event_graph(query: str, limit: int = 10) -> dict[str, Any]:
    """Hybrid semantic+lexical graph search without re-embedding the full graph.

    Semantic seeds come from the persistent sqlite-vec news index and the existing
    structured semantic search. Those seed IDs are then reranked/expanded against
    the graph snapshot. This keeps graph retrieval fast even as the graph grows.
    """
    graph = load_graph_snapshot()
    nodes = {n.get("id"): n for n in graph.get("nodes", []) if n.get("id")}
    limit = max(1, min(int(limit), 50))

    scores: dict[str, dict[str, Any]] = {}

    # 1) Lexical graph-node evidence.
    lexical_ranked = []
    for node_id, node in nodes.items():
        s = _search_score(query, node)
        if s > 0:
            lexical_ranked.append((s, node_id))
    lexical_ranked.sort(reverse=True)
    for rank, (raw, node_id) in enumerate(lexical_ranked[:100], start=1):
        rec = scores.setdefault(node_id, {"rrf": 0.0, "sources": [], "lexical_score": 0.0})
        rec["rrf"] += 1.0 / (60 + rank)
        rec["sources"].append("graph_lexical")
        rec["lexical_score"] = raw

    # 2) Semantic news-vector evidence -> event/article/entity/topic/indicator graph seeds.
    news = search_news_intelligence(query, limit=min(30, max(10, limit * 3)))
    if news.get("available", True):
        for rank, item in enumerate(news.get("results", []), start=1):
            seed_ids = []
            if item.get("doc_id"):
                seed_ids.append("article:" + str(item["doc_id"]))
            if item.get("event_id"):
                seed_ids.append("event:" + str(item["event_id"]))
            for topic in item.get("topics") or []:
                seed_ids.append("topic:" + str(topic))
            for indicator in item.get("indicators") or []:
                seed_ids.append("indicator:" + str(indicator))
            for entity in item.get("entities") or []:
                seed_ids.append("entity:" + str(entity))
            for node_id in seed_ids:
                if node_id not in nodes:
                    continue
                rec = scores.setdefault(node_id, {"rrf": 0.0, "sources": [], "lexical_score": 0.0})
                rec["rrf"] += 1.0 / (60 + rank)
                if "news_vector" not in rec["sources"]:
                    rec["sources"].append("news_vector")
                sem = item.get("semantic_similarity")
                if sem is not None:
                    rec["semantic_similarity"] = max(float(sem), float(rec.get("semantic_similarity") or -1.0))

    # 3) Existing structured semantic search seeds historical episodes/topics.
    structured = search_crisis_data(
        query=query,
        limit=min(20, max(8, limit * 2)),
        semantic=True,
        lexical_weight=0.20,
        semantic_weight=0.80,
    )
    historical_map = {
        "gfc": "historical:gfc",
        "euro": "historical:euro",
        "repo2019": "historical:repo2019",
        "covid": "historical:covid",
        "regional_banks": "historical:regional_banks",
    }
    for rank, item in enumerate(structured.get("results", []), start=1):
        candidates = []
        key = str(item.get("key") or "")
        if key in historical_map:
            candidates.append(historical_map[key])
        if item.get("type") == "indicator":
            candidates.append("indicator:" + key)
        for node_id in candidates:
            if node_id not in nodes:
                continue
            rec = scores.setdefault(node_id, {"rrf": 0.0, "sources": [], "lexical_score": 0.0})
            rec["rrf"] += 1.0 / (60 + rank)
            if "structured_semantic" not in rec["sources"]:
                rec["sources"].append("structured_semantic")
            sem = item.get("semantic_similarity")
            if sem is not None:
                rec["semantic_similarity"] = max(float(sem), float(rec.get("semantic_similarity") or -1.0))

    ranked = sorted(scores.items(), key=lambda kv: kv[1]["rrf"], reverse=True)
    results = []
    for node_id, meta in ranked[:limit]:
        results.append({
            "type": "graph_node",
            "key": node_id,
            "title": nodes[node_id].get("label"),
            "data": nodes[node_id],
            "hybrid_graph_score": round(meta["rrf"], 8),
            "retrieval_sources": meta["sources"],
            "lexical_score": round(float(meta.get("lexical_score") or 0.0), 2),
            "semantic_similarity": (
                None if meta.get("semantic_similarity") is None
                else round(float(meta["semantic_similarity"]), 4)
            ),
        })

    return {
        "query": query,
        "search_mode": "graph lexical + sqlite-vec semantic seeds + structured semantic seeds + RRF",
        "graph_stats": graph.get("stats", {}),
        "count": len(results),
        "results": results,
    }

@mcp.tool()
def get_event_neighborhood(event_id: str, hops: int = 1, limit: int = 100) -> dict[str, Any]:
    """Traverse the persisted knowledge-graph snapshot around an event/node id."""
    graph = load_graph_snapshot()
    nodes = {n.get("id"): n for n in graph.get("nodes", [])}
    target = event_id
    if target not in nodes:
        for prefix in ("event:", "historical:", "article:", "topic:", "indicator:", "entity:"):
            if prefix + event_id in nodes:
                target = prefix + event_id
                break
    if target not in nodes:
        return {"found": False, "event_id": event_id}

    max_hops = max(1, min(int(hops), 3))
    max_items = max(1, min(int(limit), 500))
    frontier = {target}
    visited = {target}
    selected_edges = []
    for _ in range(max_hops):
        nxt = set()
        for e in graph.get("edges", []):
            if e.get("src") in frontier or e.get("dst") in frontier:
                selected_edges.append(e)
                other = e.get("dst") if e.get("src") in frontier else e.get("src")
                if other and other not in visited:
                    nxt.add(other)
        visited.update(nxt)
        frontier = nxt
        if not frontier or len(visited) >= max_items:
            break
    selected_nodes = [nodes[n] for n in list(visited)[:max_items] if n in nodes]
    allowed = {n["id"] for n in selected_nodes}
    selected_edges = [e for e in selected_edges if e.get("src") in allowed and e.get("dst") in allowed][:max_items]
    return {
        "found": True,
        "root": nodes[target],
        "hops": max_hops,
        "nodes": selected_nodes,
        "edges": selected_edges,
    }

@mcp.tool()
def get_news_intelligence_status() -> dict[str, Any]:
    """Return news collection, vector DB, time-series, and graph build status."""
    status = load_news_status()
    return {
        "available": bool(status),
        "status": status,
        "graph_stats": load_graph_snapshot().get("stats", {}),
        "timeseries_rows": len(load_news_timeseries()),
    }

@mcp.tool()
def search_history(
    start_date: str | None = None,
    end_date: str | None = None,
    min_score: float | None = None,
    max_score: float | None = None,
    min_stage: int | None = None,
    limit: int = 100,
    newest_first: bool = True,
) -> dict[str, Any]:
    """Filter saved dashboard history by date, score and transmission stage."""
    rows = load_history()
    limit = max(1, min(int(limit), 365))

    try:
        start = date.fromisoformat(start_date) if start_date else None
        end = date.fromisoformat(end_date) if end_date else None
    except ValueError as e:
        return {"error": f"Dates must be YYYY-MM-DD: {e}"}

    out = []
    for row in rows:
        try:
            d = date.fromisoformat(row.get("date", ""))
        except Exception:
            continue
        score = row.get("score")
        stage = row.get("stage")
        if start and d < start:
            continue
        if end and d > end:
            continue
        if min_score is not None and (score is None or float(score) < float(min_score)):
            continue
        if max_score is not None and (score is None or float(score) > float(max_score)):
            continue
        if min_stage is not None and (stage is None or int(stage) < int(min_stage)):
            continue
        out.append(row)

    out.sort(key=lambda x: x.get("date", ""), reverse=bool(newest_first))
    return {
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "min_score": min_score,
            "max_score": max_score,
            "min_stage": min_stage,
        },
        "count": min(len(out), limit),
        "results": out[:limit],
    }

@mcp.tool()
def get_backtest_event(name: str) -> dict[str, Any]:
    """Return one historical stress episode from the walk-forward validation."""
    bt = load_backtest()
    events = bt.get("events", [])
    ranked = sorted(
        ((_search_score(name, ev), ev) for ev in events),
        key=lambda p: p[0],
        reverse=True,
    )
    if not ranked or ranked[0][0] <= 0:
        return {
            "found": False,
            "available": [{"id": e.get("id"), "name": e.get("name")} for e in events],
        }
    return {
        "found": True,
        "event": ranked[0][1],
        "method": bt.get("method"),
    }

@mcp.tool()
def get_self_improvement_state() -> dict[str, Any]:
    """Return the latest self-improvement decision, guardrails, candidates and active config."""
    agent = load_agent()
    if not agent:
        return {"available": False}
    return {
        "available": True,
        "updated_at": agent.get("updated_at"),
        "decision": agent.get("decision"),
        "policy_summary": agent.get("policy_summary"),
        "baseline": agent.get("baseline"),
        "accepted_change": agent.get("accepted_change"),
        "candidate_count": agent.get("candidate_count"),
        "top_candidates": agent.get("top_candidates"),
        "active_config": agent.get("active_config"),
        "holdout_report": agent.get("holdout_report"),
    }

@mcp.tool()
def get_neural_state(include_models: bool = False) -> dict[str, Any]:
    """Return v6 neural early-warning metrics and current inference."""
    nn = load_neural()
    if not nn:
        return {"available": False}
    result = {
        "available": True,
        "version": nn.get("version"),
        "model_type": nn.get("model_type"),
        "architecture": nn.get("architecture"),
        "ensemble_size": nn.get("ensemble_size"),
        "target": nn.get("target"),
        "temporal_split": nn.get("temporal_split"),
        "selected_threshold": nn.get("selected_threshold"),
        "current": nn.get("current"),
        "metrics": nn.get("metrics"),
        "event_evaluation": nn.get("event_evaluation"),
        "limitations": nn.get("limitations"),
    }
    if include_models:
        result["models"] = nn.get("models")
    return result

@mcp.resource("crisis://current", mime_type="application/json")
def current_resource() -> str:
    """Latest production risk snapshot."""
    return json.dumps(load_current(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://backtest", mime_type="application/json")
def backtest_resource() -> str:
    """Walk-forward historical validation payload."""
    return json.dumps(load_backtest(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://agent", mime_type="application/json")
def agent_resource() -> str:
    """Latest guarded self-improvement agent state."""
    return json.dumps(load_agent(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://neural", mime_type="application/json")
def neural_resource() -> str:
    """v6 neural early-warning payload."""
    return json.dumps(load_neural(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://news/status", mime_type="application/json")
def news_status_resource() -> str:
    """News/vector/time-series/graph intelligence build status."""
    return json.dumps(load_news_status(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://news/timeseries", mime_type="application/json")
def news_timeseries_resource() -> str:
    """News-derived topic and indicator time-series."""
    return json.dumps(load_news_timeseries(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://graph", mime_type="application/json")
def graph_resource() -> str:
    """Portable knowledge-graph snapshot."""
    return json.dumps(load_graph_snapshot(), ensure_ascii=False, indent=2)

@mcp.resource("crisis://history", mime_type="application/json")
def history_resource() -> str:
    """Saved daily dashboard history."""
    return json.dumps(load_history(), ensure_ascii=False, indent=2)

if __name__ == "__main__":
    transport = _normalize(os.getenv("MCP_TRANSPORT", "stdio"))
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            json_response=True,
        )
    else:
        mcp.run(transport="stdio")
