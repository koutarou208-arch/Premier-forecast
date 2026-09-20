#!/usr/bin/env python3
"""Persistent local intelligence store: SQLite FTS5 + sqlite-vec hybrid retrieval.

The durable source of truth is data/news_corpus.jsonl. data/news.db is rebuilt from
that portable corpus so binary sqlite-vec state is never committed across platforms.
"""
from __future__ import annotations

import json
import math
import os
import pathlib
import re
import sqlite3
import struct
from datetime import datetime, timezone
from typing import Any

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
CORPUS_PATH = DATA / "news_corpus.jsonl"
DB_PATH = pathlib.Path(os.getenv("CRISIS_NEWS_DB", str(DATA / "news.db")))
MODEL_NAME = os.getenv(
    "MCP_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
FASTEMBED_CACHE = os.path.expanduser(
    os.getenv("FASTEMBED_CACHE_PATH", "~/.cache/fastembed")
)
EMBED_DIM = 384
_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        from fastembed import TextEmbedding
        _MODEL = TextEmbedding(model_name=MODEL_NAME, cache_dir=FASTEMBED_CACHE)
    return _MODEL


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, EMBED_DIM), dtype=np.float32)
    arr = np.asarray(list(_model().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def serialize_f32(vector: np.ndarray | list[float]) -> bytes:
    values = np.asarray(vector, dtype=np.float32).reshape(-1)
    return struct.pack(f"{len(values)}f", *values)


def load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    rows = []
    for line in CORPUS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def save_corpus(rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)
    CORPUS_PATH.write_text(text, encoding="utf-8")


def semantic_text(article: dict[str, Any]) -> str:
    parts = [
        article.get("title") or "",
        article.get("summary") or "",
        "source " + str(article.get("publisher") or article.get("source_name") or ""),
        "topics " + " ".join(article.get("topics") or []),
        "indicators " + " ".join(article.get("indicators") or []),
        "entities " + " ".join(article.get("entities") or []),
        "geopolitical actors " + " ".join(article.get("geopolitical_actors") or []),
        "geopolitical modalities " + " ".join(article.get("geopolitical_modalities") or []),
        "geopolitical targets " + " ".join(article.get("geopolitical_targets") or []),
        "geopolitical responses " + " ".join(article.get("geopolitical_responses") or []),
    ]
    return "\n".join(x for x in parts if x).strip()


def _load_vec(conn: sqlite3.Connection) -> None:
    import sqlite_vec
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)


def connect(path: pathlib.Path | None = None) -> sqlite3.Connection:
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _load_vec(conn)
    return conn


def build_database(rows: list[dict[str, Any]] | None = None, path: pathlib.Path | None = None) -> dict[str, Any]:
    rows = rows if rows is not None else load_corpus()
    path = path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    conn = connect(path)
    conn.executescript(f"""
    PRAGMA journal_mode=WAL;
    CREATE TABLE articles(
        id INTEGER PRIMARY KEY,
        doc_id TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        summary TEXT,
        url TEXT,
        source_id TEXT,
        source_name TEXT,
        publisher TEXT,
        published_at TEXT,
        fetched_at TEXT,
        language TEXT,
        query_theme TEXT,
        trust REAL,
        relevance REAL,
        event_id TEXT,
        topics_json TEXT,
        indicators_json TEXT,
        entities_json TEXT,
        geopolitical INTEGER,
        geopolitical_event_score REAL,
        geopolitical_actors_json TEXT,
        geopolitical_modalities_json TEXT,
        geopolitical_targets_json TEXT,
        geopolitical_responses_json TEXT,
        reported_attributions_json TEXT,
        market_transmission_candidates_json TEXT,
        geopolitical_dimensions_json TEXT
    );
    CREATE VIRTUAL TABLE article_fts USING fts5(
        title, summary, publisher, topics, indicators, entities,
        content='articles', content_rowid='id',
        tokenize='unicode61 remove_diacritics 2'
    );
    CREATE VIRTUAL TABLE article_vec USING vec0(
        embedding float[{EMBED_DIM}]
    );
    CREATE TABLE events(
        event_id TEXT PRIMARY KEY,
        label TEXT,
        topic TEXT,
        first_seen TEXT,
        last_seen TEXT,
        article_count INTEGER,
        max_relevance REAL,
        entities_json TEXT,
        indicators_json TEXT
    );
    CREATE INDEX idx_articles_published ON articles(published_at);
    CREATE INDEX idx_articles_event ON articles(event_id);
    """)

    texts = [semantic_text(r) for r in rows]
    vectors = embed_texts(texts) if rows else np.empty((0, EMBED_DIM), dtype=np.float32)

    for idx, (article, vec) in enumerate(zip(rows, vectors), start=1):
        conn.execute(
            """INSERT INTO articles(
                id, doc_id, title, summary, url, source_id, source_name, publisher,
                published_at, fetched_at, language, query_theme, trust, relevance,
                event_id, topics_json, indicators_json, entities_json,
                geopolitical, geopolitical_event_score, geopolitical_actors_json,
                geopolitical_modalities_json, geopolitical_targets_json,
                geopolitical_responses_json, reported_attributions_json,
                market_transmission_candidates_json, geopolitical_dimensions_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                idx,
                article.get("doc_id"),
                article.get("title") or "",
                article.get("summary") or "",
                article.get("url"),
                article.get("source_id"),
                article.get("source_name"),
                article.get("publisher"),
                article.get("published_at"),
                article.get("fetched_at"),
                article.get("language"),
                article.get("query_theme"),
                float(article.get("trust") or 0.5),
                float(article.get("relevance") or 0.0),
                article.get("event_id"),
                json.dumps(article.get("topics") or [], ensure_ascii=False),
                json.dumps(article.get("indicators") or [], ensure_ascii=False),
                json.dumps(article.get("entities") or [], ensure_ascii=False),
                1 if article.get("geopolitical") else 0,
                float(article.get("geopolitical_event_score") or 0.0),
                json.dumps(article.get("geopolitical_actors") or [], ensure_ascii=False),
                json.dumps(article.get("geopolitical_modalities") or [], ensure_ascii=False),
                json.dumps(article.get("geopolitical_targets") or [], ensure_ascii=False),
                json.dumps(article.get("geopolitical_responses") or [], ensure_ascii=False),
                json.dumps(article.get("reported_attributions") or [], ensure_ascii=False),
                json.dumps(article.get("market_transmission_candidates") or [], ensure_ascii=False),
                json.dumps(article.get("geopolitical_dimensions") or {}, ensure_ascii=False),
            ),
        )
        conn.execute(
            "INSERT INTO article_fts(rowid,title,summary,publisher,topics,indicators,entities) VALUES(?,?,?,?,?,?,?)",
            (
                idx,
                article.get("title") or "",
                article.get("summary") or "",
                article.get("publisher") or "",
                " ".join(article.get("topics") or []),
                " ".join(article.get("indicators") or []),
                " ".join(article.get("entities") or []),
            ),
        )
        conn.execute(
            "INSERT INTO article_vec(rowid,embedding) VALUES(?,?)",
            (idx, serialize_f32(vec)),
        )

    events: dict[str, dict[str, Any]] = {}
    for r in rows:
        eid = r.get("event_id")
        if not eid:
            continue
        e = events.setdefault(
            eid,
            {
                "event_id": eid,
                "label": r.get("event_label") or r.get("title"),
                "topic": (r.get("topics") or ["unclassified"])[0],
                "first_seen": r.get("published_at"),
                "last_seen": r.get("published_at"),
                "article_count": 0,
                "max_relevance": 0.0,
                "entities": set(),
                "indicators": set(),
            },
        )
        e["article_count"] += 1
        if r.get("published_at") and (not e["first_seen"] or r["published_at"] < e["first_seen"]):
            e["first_seen"] = r["published_at"]
        if r.get("published_at") and (not e["last_seen"] or r["published_at"] > e["last_seen"]):
            e["last_seen"] = r["published_at"]
        e["max_relevance"] = max(e["max_relevance"], float(r.get("relevance") or 0.0))
        e["entities"].update(r.get("entities") or [])
        e["indicators"].update(r.get("indicators") or [])

    for e in events.values():
        conn.execute(
            "INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?)",
            (
                e["event_id"], e["label"], e["topic"], e["first_seen"], e["last_seen"],
                e["article_count"], e["max_relevance"],
                json.dumps(sorted(e["entities"]), ensure_ascii=False),
                json.dumps(sorted(e["indicators"]), ensure_ascii=False),
            ),
        )

    conn.commit()
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    vec_version = conn.execute("SELECT vec_version()").fetchone()[0]
    conn.close()
    return {
        "path": str(path),
        "articles": count,
        "events": len(events),
        "embedding_model": MODEL_NAME,
        "vector_dim": EMBED_DIM,
        "sqlite_vec_version": vec_version,
    }


def ensure_database() -> pathlib.Path:
    if not DB_PATH.exists():
        build_database()
    return DB_PATH


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_+.-]{2,}|[ぁ-んァ-ヶ一-龯ー]{2,}", query)
    tokens = [t.replace('"', '') for t in tokens[:12]]
    return " OR ".join(f'"{t}"' for t in tokens)


def _row_to_article(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    list_fields = (
        "topics_json", "indicators_json", "entities_json",
        "geopolitical_actors_json", "geopolitical_modalities_json",
        "geopolitical_targets_json", "geopolitical_responses_json",
        "reported_attributions_json", "market_transmission_candidates_json",
    )
    for field in list_fields:
        key = field.replace("_json", "")
        try:
            out[key] = json.loads(out.pop(field) or "[]")
        except Exception:
            out[key] = []
            out.pop(field, None)
    try:
        out["geopolitical_dimensions"] = json.loads(out.pop("geopolitical_dimensions_json") or "{}")
    except Exception:
        out["geopolitical_dimensions"] = {}
        out.pop("geopolitical_dimensions_json", None)
    out["geopolitical"] = bool(out.get("geopolitical"))
    return out


def _recency_score(published_at: str | None, half_life_days: float = 21.0) -> float:
    if not published_at:
        return 0.0
    try:
        d = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - d).total_seconds() / 86400.0)
        return math.exp(-math.log(2.0) * age_days / half_life_days)
    except Exception:
        return 0.0


def search_news(
    query: str,
    limit: int = 10,
    *,
    vector_k: int = 60,
    lexical_k: int = 60,
    rrf_k: int = 60,
    recency_weight: float = 0.08,
    trust_weight: float = 0.04,
) -> dict[str, Any]:
    """BM25/FTS + vector cosine + metadata rerank.

    Base rank fusion uses reciprocal-rank fusion (RRF), which is robust when the
    lexical and vector score scales are not directly comparable.
    """
    ensure_database()
    conn = connect()
    limit = max(1, min(int(limit), 50))
    lexical: list[tuple[int, float]] = []
    q = _fts_query(query)
    if q:
        try:
            lexical = [
                (int(r["id"]), float(r["bm25"]))
                for r in conn.execute(
                    """SELECT a.id, bm25(article_fts) AS bm25
                       FROM article_fts
                       JOIN articles a ON a.id=article_fts.rowid
                       WHERE article_fts MATCH ?
                       ORDER BY bm25(article_fts)
                       LIMIT ?""",
                    (q, lexical_k),
                ).fetchall()
            ]
        except sqlite3.OperationalError:
            lexical = []

    qvec = embed_texts([query])[0]
    vector = [
        (int(r["rowid"]), float(r["distance"]))
        for r in conn.execute(
            """SELECT rowid,distance FROM article_vec
               WHERE embedding MATCH ?
               ORDER BY distance
               LIMIT ?""",
            (serialize_f32(qvec), vector_k),
        ).fetchall()
    ]

    scores: dict[int, dict[str, Any]] = {}
    for rank, (rid, bm25_score) in enumerate(lexical, start=1):
        s = scores.setdefault(rid, {"rrf": 0.0, "lexical_rank": None, "vector_rank": None})
        s["rrf"] += 1.0 / (rrf_k + rank)
        s["lexical_rank"] = rank
        s["bm25"] = bm25_score
    for rank, (rid, distance) in enumerate(vector, start=1):
        s = scores.setdefault(rid, {"rrf": 0.0, "lexical_rank": None, "vector_rank": None})
        s["rrf"] += 1.0 / (rrf_k + rank)
        s["vector_rank"] = rank
        s["vector_distance"] = distance
        s["semantic_similarity"] = max(-1.0, min(1.0, 1.0 - distance * distance / 2.0))

    ids = list(scores)
    if not ids:
        conn.close()
        return {"query": query, "count": 0, "results": [], "mode": "hybrid_rrf"}

    placeholders = ",".join("?" for _ in ids)
    articles = {
        int(r["id"]): _row_to_article(r)
        for r in conn.execute(f"SELECT * FROM articles WHERE id IN ({placeholders})", ids).fetchall()
    }

    ranked = []
    for rid, meta in scores.items():
        article = articles.get(rid)
        if not article:
            continue
        recency = _recency_score(article.get("published_at"))
        trust = float(article.get("trust") or 0.5)
        final = meta["rrf"] + recency_weight * recency / 100.0 + trust_weight * trust / 100.0
        ranked.append((final, article, meta, recency, trust))
    ranked.sort(key=lambda x: x[0], reverse=True)

    out = []
    for final, article, meta, recency, trust in ranked[:limit]:
        out.append({
            **article,
            "hybrid_score": round(final, 6),
            "lexical_rank": meta.get("lexical_rank"),
            "vector_rank": meta.get("vector_rank"),
            "semantic_similarity": None if meta.get("semantic_similarity") is None else round(meta["semantic_similarity"], 4),
            "recency_score": round(recency, 4),
            "trust_score": round(trust, 3),
        })
    conn.close()
    return {
        "query": query,
        "mode": "BM25_FTS5+sqlite_vec+RRF+recency+trust",
        "embedding_model": MODEL_NAME,
        "count": len(out),
        "results": out,
    }


def get_event(event_id: str) -> dict[str, Any] | None:
    ensure_database()
    conn = connect()
    row = conn.execute("SELECT * FROM events WHERE event_id=?", (event_id,)).fetchone()
    if not row:
        conn.close()
        return None
    event = dict(row)
    for field in ("entities_json", "indicators_json"):
        event[field.replace("_json", "")] = json.loads(event.pop(field) or "[]")
    event["articles"] = [
        _row_to_article(r)
        for r in conn.execute(
            "SELECT * FROM articles WHERE event_id=? ORDER BY published_at DESC LIMIT 50",
            (event_id,),
        ).fetchall()
    ]
    conn.close()
    return event


def latest_news(limit: int = 20) -> list[dict[str, Any]]:
    ensure_database()
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM articles ORDER BY published_at DESC LIMIT ?",
        (max(1, min(int(limit), 100)),),
    ).fetchall()
    out = [_row_to_article(r) for r in rows]
    conn.close()
    return out
