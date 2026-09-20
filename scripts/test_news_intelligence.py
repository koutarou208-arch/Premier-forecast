#!/usr/bin/env python3
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intelligence_store import search_news, latest_news

status = json.loads((ROOT / "data" / "news_intelligence_status.json").read_text())
assert status["articles_retained"] > 0, status
assert status["vector_db"]["articles"] == status["articles_retained"], status
assert status["vector_db"]["vector_dim"] == 384, status
assert status["graph_db"]["nodes"] > 0, status

funding = search_news("short term funding liquidity repo stress", limit=8)
assert funding["count"] > 0, funding
assert funding["mode"].startswith("BM25_FTS5+sqlite_vec"), funding

japan = search_news("日銀 金融政策 銀行 流動性", limit=8)
assert japan["count"] > 0, japan

latest = latest_news(5)
assert latest, "no latest news"

graph = json.loads((ROOT / "data" / "graph_snapshot.json").read_text())
kinds = {n["kind"] for n in graph["nodes"]}
assert {"Article","Event","Topic","Indicator","HistoricalEpisode"}.issubset(kinds), kinds
rels = {e["rel"] for e in graph["edges"]}
assert {"EVIDENCE_FOR","ABOUT","IMPACTS","PRECEDES"}.issubset(rels), rels

series = json.loads((ROOT / "data" / "news_timeseries.json").read_text())
assert series, "empty timeseries"

geo_status = json.loads((ROOT / "data" / "geopolitical_status.json").read_text())
geo_series = json.loads((ROOT / "data" / "geopolitical_timeseries.json").read_text())
assert 0 <= geo_status["geopolitical_escalation_index"] <= 100, geo_status
assert geo_status["model_boundary"]["changes_stage_0_4"] is False, geo_status
assert geo_status["model_boundary"]["changes_financial_crisis_score"] is False, geo_status
assert geo_series, "empty geopolitical timeseries"

if geo_status["counts"]["events"] > 0:
    assert {"Actor","Target","Modality","Response"} & kinds, kinds
    assert {"MENTIONS_ACTOR","TARGETS","USES_MODALITY"} & rels, rels

print(json.dumps({
    "articles": status["articles_retained"],
    "events": status["events"],
    "timeseries_rows": status["timeseries_rows"],
    "graph_nodes": graph["stats"]["nodes"],
    "graph_edges": graph["stats"]["edges"],
    "funding_top": [x["title"] for x in funding["results"][:3]],
    "japan_top": [x["title"] for x in japan["results"][:3]],
    "geopolitical_index": geo_status["geopolitical_escalation_index"],
    "geopolitical_events_90d": geo_status["counts"]["events"],
}, ensure_ascii=False))
