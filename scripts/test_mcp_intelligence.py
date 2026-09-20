#!/usr/bin/env python3
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["MCP_EMBEDDINGS"] = "on"

import mcp_server as m

status = m.get_news_intelligence_status()
assert status["available"], status
assert status["status"]["articles_retained"] > 0, status

news = m.search_news_intelligence("bank funding liquidity stress", limit=5)
assert news.get("count", 0) > 0, news

all_search = m.search_all_intelligence("信用収縮と銀行の資金調達悪化", limit=8)
assert all_search["merged"], all_search
assert any(x["domain"] == "news" for x in all_search["merged"]), all_search

series = m.get_news_timeseries(days=365)
assert series["count"] > 0, series

geo = m.get_geopolitical_state()
assert geo["available"], geo
geo_ready = geo.get("geopolitical_escalation_index") is not None
if geo_ready:
    assert 0 <= geo["geopolitical_escalation_index"] <= 100, geo
    assert geo["model_boundary"]["changes_stage_0_4"] is False, geo
    geo_search = m.search_geopolitical_events("Russia NATO sabotage critical infrastructure", limit=8)
    assert geo_search.get("count", 0) > 0, geo_search
    geo_timeline = m.get_geopolitical_timeline(days=365)
    assert geo_timeline["count"] > 0, geo_timeline
else:
    assert geo.get("status") == "pending", geo
    geo_search = {"count": 0}
    geo_timeline = {"count": 0}

graph = m.search_event_graph("repo funding liquidity", limit=8)
assert graph["count"] > 0, graph

snapshot = m.load_graph_snapshot()
event_nodes = [n for n in snapshot.get("nodes", []) if n.get("kind") in {"Event", "HistoricalEpisode"}]
assert event_nodes, "no graph event nodes"
neighborhood = m.get_event_neighborhood(event_nodes[0]["id"], hops=1, limit=80)
assert neighborhood["found"], neighborhood
assert neighborhood["edges"], neighborhood

print(json.dumps({
    "news_articles": status["status"]["articles_retained"],
    "news_search_top": [x["title"] for x in news["results"][:3]],
    "cross_domain_count": len(all_search["merged"]),
    "timeseries_rows": series["count"],
    "graph_results": graph["count"],
    "neighborhood_nodes": len(neighborhood["nodes"]),
    "neighborhood_edges": len(neighborhood["edges"]),
    "geopolitical_index": geo.get("geopolitical_escalation_index"),
    "geopolitical_results": geo_search["count"],
    "geopolitical_timeline_rows": geo_timeline["count"],
}, ensure_ascii=False))
