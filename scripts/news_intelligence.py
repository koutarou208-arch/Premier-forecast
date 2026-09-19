#!/usr/bin/env python3
"""Collect finance news, enrich it, persist a portable corpus, rebuild vector DB,
derive time-series signals, and materialize a Ladybug property graph.
"""
from __future__ import annotations

import calendar
import csv
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any

import feedparser
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intelligence_store import build_database, embed_texts, load_corpus, save_corpus, semantic_text

DATA = ROOT / "data"
SOURCES_PATH = DATA / "news_sources.json"
TAXONOMY_PATH = DATA / "news_taxonomy.json"
TIMESERIES_PATH = DATA / "news_timeseries.json"
GRAPH_SNAPSHOT_PATH = DATA / "graph_snapshot.json"
STATUS_PATH = DATA / "news_intelligence_status.json"
BACKTEST_PATH = DATA / "backtest.json"
GRAPH_DB_PATH = pathlib.Path(os.getenv("CRISIS_GRAPH_DB", str(DATA / "knowledge_graph")))

USER_AGENT = "global-financial-crisis-watch-news-intelligence/1.0"
EVENT_SIM_THRESHOLD = 0.68
EVENT_GAP_HOURS = 96


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def strip_html(value: str | None) -> str:
    if not value:
        return ""
    parser = _TextExtractor()
    try:
        parser.feed(html.unescape(value))
        text = " ".join(parser.parts)
    except Exception:
        text = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", text).strip()


def utc_iso_from_entry(entry) -> str:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        value = getattr(entry, attr, None)
        if value:
            ts = calendar.timegm(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_feed(url: str, timeout: int = 18):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return feedparser.parse(r.read())


def google_news_url(query: str, locale: str, country: str, ceid: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote_plus(query)
        + f"&hl={urllib.parse.quote(locale)}&gl={urllib.parse.quote(country)}&ceid={urllib.parse.quote(ceid)}"
    )


def publisher_from_entry(entry, source_name: str) -> str:
    source = getattr(entry, "source", None)
    if source:
        try:
            title = source.get("title")
            if title:
                return str(title)
        except Exception:
            pass
    title = str(getattr(entry, "title", "") or "")
    if " - " in title:
        suffix = title.rsplit(" - ", 1)[1].strip()
        if 1 <= len(suffix) <= 80:
            return suffix
    return source_name


def canonical_title(title: str) -> str:
    title = re.sub(r"\s+-\s+[^-]{1,80}$", "", title).strip()
    return re.sub(r"\s+", " ", title)


def article_doc_id(title: str, publisher: str, published_at: str) -> str:
    day = (published_at or "")[:10]
    raw = (canonical_title(title).lower() + "|" + publisher.lower() + "|" + day).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def collect_from_source(source: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    try:
        url = source["url"]
        feed = fetch_feed(url)
        if getattr(feed, "bozo", False) and not feed.entries:
            raise RuntimeError(str(getattr(feed, "bozo_exception", "RSS parse failed")))
        fetched = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        rows = []
        for entry in feed.entries[:100]:
            title = strip_html(str(getattr(entry, "title", "") or ""))
            if not title:
                continue
            published_at = utc_iso_from_entry(entry)
            publisher = publisher_from_entry(entry, source["name"])
            summary = strip_html(str(getattr(entry, "summary", "") or getattr(entry, "description", "") or ""))
            url_value = str(getattr(entry, "link", "") or "")
            rows.append({
                "doc_id": article_doc_id(title, publisher, published_at),
                "title": title,
                "summary": summary[:1200],
                "url": url_value,
                "source_id": source["id"],
                "source_name": source["name"],
                "publisher": publisher,
                "published_at": published_at,
                "fetched_at": fetched,
                "language": source.get("language") or ("ja" if source.get("locale") == "ja" else "en"),
                "query_theme": source.get("query_theme"),
                "trust": float(source.get("trust", 0.72)),
            })
        return rows, None
    except Exception as e:
        return [], f"{source.get('id')}: {type(e).__name__}: {e}"


def build_source_list(config: dict[str, Any]) -> list[dict[str, Any]]:
    sources = []
    for x in config.get("official_rss", []):
        item = dict(x)
        item["language"] = "en"
        item["query_theme"] = "official"
        sources.append(item)
    for q in config.get("google_news_queries", []):
        sources.append({
            "id": "gnews_" + q["id"],
            "name": "Google News RSS — " + q["id"],
            "url": google_news_url(q["query"], q.get("locale", "en-US"), q.get("country", "US"), q.get("ceid", "US:en")),
            "language": "ja" if str(q.get("locale", "")).startswith("ja") else "en",
            "query_theme": q["id"],
            "trust": 0.72,
        })
    return sources


def classify_articles(rows: list[dict[str, Any]], taxonomy: dict[str, Any]) -> None:
    topics = taxonomy["topics"]
    descriptor_records = []
    for topic, cfg in topics.items():
        for desc in cfg.get("descriptors", []):
            descriptor_records.append((topic, desc))
    descriptor_vecs = embed_texts([x[1] for x in descriptor_records])
    article_vecs = embed_texts([semantic_text(r) for r in rows])

    entity_map = taxonomy.get("entities", {})
    for article, avec in zip(rows, article_vecs):
        text = (article.get("title", "") + " " + article.get("summary", "")).lower()
        topic_best: dict[str, float] = {}
        for (topic, _), dvec in zip(descriptor_records, descriptor_vecs):
            sim = float(np.dot(avec, dvec))
            topic_best[topic] = max(topic_best.get(topic, -1.0), sim)

        for topic, cfg in topics.items():
            lexical_hit = any(alias.lower() in text for alias in cfg.get("aliases", []))
            if lexical_hit:
                topic_best[topic] = max(topic_best.get(topic, 0.0), 0.58)

        ordered = sorted(topic_best.items(), key=lambda x: x[1], reverse=True)
        selected = [t for t, s in ordered[:3] if s >= 0.30]
        if not selected and ordered:
            selected = [ordered[0][0]]
        article["topics"] = selected
        article["relevance"] = round(max([topic_best.get(t, 0.0) for t in selected] or [0.0]), 4)
        indicators = set()
        for topic in selected:
            indicators.update(topics[topic].get("indicators", []))
        article["indicators"] = sorted(indicators)
        entities = []
        original_text = article.get("title", "") + " " + article.get("summary", "")
        lowered = original_text.lower()
        for entity, aliases in entity_map.items():
            if any(alias.lower() in lowered for alias in aliases):
                entities.append(entity)
        if article.get("publisher") and article["publisher"] not in entities:
            entities.append(article["publisher"])
        article["entities"] = sorted(set(entities))


def parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def cluster_events(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    ordered = sorted(rows, key=lambda r: (r.get("published_at") or "", r.get("doc_id") or ""))
    vectors = embed_texts([semantic_text(r) for r in ordered])
    clusters: list[dict[str, Any]] = []

    for article, vector in zip(ordered, vectors):
        topic = (article.get("topics") or ["unclassified"])[0]
        dt = parse_dt(article.get("published_at"))
        best_idx = None
        best_sim = -1.0
        for i in range(len(clusters) - 1, -1, -1):
            c = clusters[i]
            gap = (dt - c["last_dt"]).total_seconds() / 3600.0
            if gap > EVENT_GAP_HOURS:
                continue
            if gap < -24:
                continue
            if c["topic"] != topic:
                continue
            sim = float(np.dot(vector, c["centroid"]))
            if sim > best_sim:
                best_sim = sim
                best_idx = i

        if best_idx is not None and best_sim >= EVENT_SIM_THRESHOLD:
            c = clusters[best_idx]
            n = c["count"]
            centroid = (c["centroid"] * n + vector) / (n + 1)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            c["centroid"] = centroid
            c["count"] += 1
            c["last_dt"] = max(c["last_dt"], dt)
            c["doc_ids"].append(article["doc_id"])
            article["event_id"] = c["event_id"]
            article["event_label"] = c["label"]
        else:
            event_id = "evt_" + hashlib.sha1((topic + "|" + article["doc_id"]).encode("utf-8")).hexdigest()[:16]
            label = canonical_title(article["title"])[:140]
            clusters.append({
                "event_id": event_id,
                "topic": topic,
                "centroid": vector.copy(),
                "count": 1,
                "last_dt": dt,
                "doc_ids": [article["doc_id"]],
                "label": label,
            })
            article["event_id"] = event_id
            article["event_label"] = label


def prune_and_merge(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], retention_days: int, max_articles: int) -> list[dict[str, Any]]:
    merged = {r.get("doc_id"): r for r in existing if r.get("doc_id")}
    for row in incoming:
        old = merged.get(row["doc_id"], {})
        merged[row["doc_id"]] = {**old, **row}
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    rows = [r for r in merged.values() if parse_dt(r.get("published_at")) >= cutoff]
    rows.sort(key=lambda r: (r.get("published_at") or "", r.get("doc_id") or ""), reverse=True)
    rows = rows[:max_articles]
    rows.sort(key=lambda r: (r.get("published_at") or "", r.get("doc_id") or ""))
    return rows


def build_timeseries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in rows:
        day = (r.get("published_at") or "")[:10]
        if not day:
            continue
        items = [("topic", x) for x in r.get("topics", [])] + [("indicator", x) for x in r.get("indicators", [])]
        for kind, key in items:
            b = buckets.setdefault((day, kind, key), {
                "day": day, "kind": kind, "key": key, "article_count": 0,
                "events": set(), "relevance_sum": 0.0, "max_relevance": 0.0,
                "publishers": set(),
            })
            b["article_count"] += 1
            if r.get("event_id"):
                b["events"].add(r["event_id"])
            rel = float(r.get("relevance") or 0.0)
            b["relevance_sum"] += rel
            b["max_relevance"] = max(b["max_relevance"], rel)
            if r.get("publisher"):
                b["publishers"].add(r["publisher"])
    out = []
    for b in buckets.values():
        out.append({
            "day": b["day"],
            "kind": b["kind"],
            "key": b["key"],
            "article_count": b["article_count"],
            "event_count": len(b["events"]),
            "publisher_count": len(b["publishers"]),
            "avg_relevance": round(b["relevance_sum"] / max(1, b["article_count"]), 4),
            "max_relevance": round(b["max_relevance"], 4),
        })
    return sorted(out, key=lambda x: (x["day"], x["kind"], x["key"]))


HISTORICAL_MAP = {
    "gfc": ("systemic_crisis", ["ig_credit","hy_credit","leveraged_credit","funding_market","banking_stress"]),
    "euro": ("europe_sovereign", ["europe","banking_stress"]),
    "repo2019": ("funding_liquidity", ["funding_market","rates_liquidity"]),
    "covid": ("systemic_crisis", ["financial_stress","rates_liquidity","funding_market","banking_stress"]),
    "regional_banks": ("banking", ["banking_stress","funding_market"]),
}


def build_graph_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add_node(node_id, kind, label, **meta):
        nodes[node_id] = {"id": node_id, "kind": kind, "label": label, "meta": meta}

    def add_edge(src, dst, rel, weight=1.0, **meta):
        edges[(src, dst, rel)] = {"src": src, "dst": dst, "rel": rel, "weight": round(float(weight),4), "meta": meta}

    events: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        aid = "article:" + r["doc_id"]
        add_node(aid, "Article", r["title"], published_at=r.get("published_at"), url=r.get("url"))
        sid = "source:" + (r.get("publisher") or r.get("source_name") or "unknown")
        add_node(sid, "Source", r.get("publisher") or r.get("source_name") or "unknown")
        add_edge(aid, sid, "PUBLISHED_BY", r.get("trust") or 0.5)
        eid = "event:" + str(r.get("event_id") or "unclustered")
        events[str(r.get("event_id") or "unclustered")].append(r)
        add_node(eid, "Event", r.get("event_label") or r["title"])
        add_edge(aid, eid, "EVIDENCE_FOR", r.get("relevance") or 0.0, published_at=r.get("published_at"))
        day = (r.get("published_at") or "")[:10]
        if day:
            did = "day:" + day
            add_node(did, "Day", day)
            add_edge(eid, did, "OBSERVED_ON", 1.0)
        for topic in r.get("topics", []):
            tid = "topic:" + topic
            add_node(tid, "Topic", topic)
            add_edge(eid, tid, "ABOUT", r.get("relevance") or 0.0)
        for indicator in r.get("indicators", []):
            iid = "indicator:" + indicator
            add_node(iid, "Indicator", indicator)
            add_edge(eid, iid, "IMPACTS", r.get("relevance") or 0.0)
        for entity in r.get("entities", []):
            nid = "entity:" + entity
            add_node(nid, "Entity", entity)
            add_edge(aid, nid, "MENTIONS", 1.0)

    # Temporal edges between news event clusters in the same top-level topic.
    event_meta = []
    for eid, arts in events.items():
        dates = sorted(parse_dt(a.get("published_at")) for a in arts)
        top = (arts[0].get("topics") or ["unclassified"])[0]
        event_meta.append((top, dates[0], eid))
    by_topic: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
    for topic, first, eid in event_meta:
        by_topic[topic].append((first, eid))
    for topic, seq in by_topic.items():
        seq.sort()
        for (d1,e1),(d2,e2) in zip(seq,seq[1:]):
            add_edge("event:"+e1, "event:"+e2, "PRECEDES", 1.0, gap_days=round((d2-d1).total_seconds()/86400.0,2), topic=topic)

    # Seed known historical validation episodes into the same graph.
    try:
        bt = json.loads(BACKTEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        bt = {}
    historical = []
    for ev in bt.get("events", []):
        key = ev.get("id")
        topic, indicators = HISTORICAL_MAP.get(key, ("systemic_crisis", []))
        hid = "historical:" + str(key)
        add_node(
            hid, "HistoricalEpisode", ev.get("name") or str(key),
            start=ev.get("start"), end=ev.get("end"), max_score=ev.get("max_score"),
            max_stage=ev.get("max_stage"), reference_date=ev.get("reference_date")
        )
        tid = "topic:" + topic
        add_node(tid, "Topic", topic)
        add_edge(hid, tid, "ABOUT", 1.0)
        for ind in indicators:
            iid = "indicator:" + ind
            add_node(iid, "Indicator", ind)
            add_edge(hid, iid, "IMPACTS", 1.0)
        historical.append((ev.get("start") or "", hid))
    historical.sort()
    for (_,a),(_,b) in zip(historical,historical[1:]):
        add_edge(a,b,"PRECEDES",1.0)

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "nodes": list(nodes.values()),
        "edges": list(edges.values()),
        "stats": {
            "nodes": len(nodes),
            "edges": len(edges),
            "articles": sum(1 for n in nodes.values() if n["kind"]=="Article"),
            "events": sum(1 for n in nodes.values() if n["kind"]=="Event"),
            "historical_episodes": sum(1 for n in nodes.values() if n["kind"]=="HistoricalEpisode"),
        },
    }


def build_ladybug_graph(snapshot: dict[str, Any]) -> dict[str, Any]:
    import ladybug
    if GRAPH_DB_PATH.exists():
        if GRAPH_DB_PATH.is_dir():
            shutil.rmtree(GRAPH_DB_PATH)
        else:
            GRAPH_DB_PATH.unlink()

    db = ladybug.Database(str(GRAPH_DB_PATH))
    conn = ladybug.Connection(db)
    conn.execute("CREATE NODE TABLE Node(id STRING, kind STRING, label STRING, metadata STRING, PRIMARY KEY(id))")
    conn.execute("CREATE REL TABLE Related(FROM Node TO Node, rel STRING, weight DOUBLE, metadata STRING)")

    # Ladybug recommends COPY FROM for bulk database creation. The graph DB is
    # derived from the portable snapshot, so rebuilding is deterministic.
    with tempfile.TemporaryDirectory(prefix="crisis_graph_") as td:
        td_path = pathlib.Path(td)
        nodes_csv = td_path / "nodes.csv"
        edges_csv = td_path / "edges.csv"

        with nodes_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "kind", "label", "metadata"])
            for n in snapshot["nodes"]:
                w.writerow([
                    n["id"], n["kind"], n["label"],
                    json.dumps(n.get("meta") or {}, ensure_ascii=False, separators=(",", ":")),
                ])

        # Relationship COPY expects FROM and TO primary keys as the first two
        # columns, followed by relationship properties in schema order.
        with edges_csv.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            for e in snapshot["edges"]:
                w.writerow([
                    e["src"], e["dst"], e["rel"], float(e.get("weight") or 0.0),
                    json.dumps(e.get("meta") or {}, ensure_ascii=False, separators=(",", ":")),
                ])

        nodes_path = nodes_csv.as_posix().replace("'", "''")
        edges_path = edges_csv.as_posix().replace("'", "''")
        conn.execute(f"COPY Node FROM '{nodes_path}' (header=true)")
        conn.execute(f"COPY Related FROM '{edges_path}'")

    result = conn.execute("MATCH (n:Node) RETURN count(n)")
    count = result.get_next()[0] if result.has_next() else 0
    del result
    conn.close()
    db.close()
    return {
        "path": str(GRAPH_DB_PATH),
        "nodes": int(count),
        "edges": len(snapshot["edges"]),
        "engine": "LadybugDB",
        "load_mode": "CSV COPY FROM",
    }


def main():
    config = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    source_list = build_source_list(config)
    incoming = []
    failures = []
    source_counts = {}
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(collect_from_source, source): source for source in source_list}
        for future in as_completed(futures):
            source = futures[future]
            try:
                rows, error = future.result()
            except Exception as e:
                rows, error = [], f"{source.get('id')}: {type(e).__name__}: {e}"
            source_counts[source["id"]] = len(rows)
            incoming.extend(rows)
            if error:
                failures.append(error)

    existing = load_corpus()
    combined = prune_and_merge(
        existing, incoming,
        int(config.get("retention_days", 365)),
        int(config.get("max_articles", 5000)),
    )
    classify_articles(combined, taxonomy)
    # Filter only after semantic classification. Official feeds get a slightly lower floor.
    combined = [
        r for r in combined
        if float(r.get("relevance") or 0.0) >= (0.20 if float(r.get("trust") or 0) >= 0.95 else 0.25)
    ]
    cluster_events(combined)
    save_corpus(combined)

    timeseries = build_timeseries(combined)
    TIMESERIES_PATH.write_text(json.dumps(timeseries, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    vector_status = build_database(combined)

    snapshot = build_graph_snapshot(combined)
    GRAPH_SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

    graph_error = None
    graph_status = {}
    try:
        graph_status = build_ladybug_graph(snapshot)
    except Exception as e:
        graph_error = f"{type(e).__name__}: {e}"
        failures.append("graph: " + graph_error)

    event_ids = {r.get("event_id") for r in combined if r.get("event_id")}
    status = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "sources": len(source_list),
        "source_counts": source_counts,
        "incoming_entries": len(incoming),
        "articles_retained": len(combined),
        "events": len(event_ids),
        "timeseries_rows": len(timeseries),
        "vector_db": vector_status,
        "graph_db": graph_status,
        "graph_error": graph_error,
        "failures": failures,
        "copyright_mode": "RSS metadata/title/short-summary only; no full article-body mirroring",
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
