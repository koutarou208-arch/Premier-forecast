#!/usr/bin/env python3
import json
import pathlib
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from geopolitical_intelligence import (
    build_geopolitical_events,
    build_geopolitical_status,
    build_geopolitical_timeseries,
    enrich_geopolitical_articles,
    load_taxonomy,
)

taxonomy = load_taxonomy()

rows = [
    {
        "doc_id": "a1",
        "event_id": "evt1",
        "event_label": "Airport drone incident",
        "title": "Germany blames Russia for explosive drone near NATO logistics airport",
        "summary": "Fighter jets were scrambled and critical infrastructure protection was raised.",
        "publisher": "Example News",
        "published_at": "2026-08-04T10:00:00Z",
        "query_theme": "geopolitics_hybrid_europe",
    },
    {
        "doc_id": "a2",
        "event_id": "evt2",
        "event_label": "Rail incident under investigation",
        "title": "France investigates railway obstruction and possible involvement by Russia",
        "summary": "Authorities opened an investigation. No evidence has established responsibility.",
        "publisher": "Example News",
        "published_at": "2026-09-11T10:00:00Z",
        "query_theme": "geopolitics_infrastructure",
    },
    {
        "doc_id": "a3",
        "event_id": "evt3",
        "event_label": "Military threat",
        "title": "Russia says NATO facilities could become a legitimate target",
        "summary": "European governments issued a joint statement and sanctions response.",
        "publisher": "Example News",
        "published_at": "2026-09-18T10:00:00Z",
        "query_theme": "geopolitics_threats",
    },
]

enrich_geopolitical_articles(rows, taxonomy)

assert rows[0]["geopolitical"] is True
assert "Russia" in rows[0]["geopolitical_actors"]
assert "explosive_drone" in rows[0]["geopolitical_modalities"]
assert rows[0]["geopolitical_dimensions"]["critical_infrastructure"] is True
assert rows[0]["geopolitical_dimensions"]["military_response"] is True
assert rows[0]["reported_attributions"] == [{"actor": "Russia", "status": "reported_attributed"}], rows[0]["reported_attributions"]

assert rows[1]["geopolitical"] is True
assert rows[1]["reported_attributions"]
assert all(
    x["status"] in {"suspected", "reported_attribution_disputed"}
    for x in rows[1]["reported_attributions"]
)
assert rows[1]["geopolitical_event_score"] < rows[0]["geopolitical_event_score"]

assert rows[2]["geopolitical_dimensions"]["explicit_threat"] is True

events = build_geopolitical_events(rows)
assert len(events) == 3
assert any(e["event_id"] == "evt1" for e in events)

series = build_geopolitical_timeseries(rows)
assert any(x["kind"] == "overall" for x in series)
assert any(x["kind"] == "reported_attribution" and x["key"] == "Russia" for x in series)

status = build_geopolitical_status(
    rows,
    window_days=90,
    as_of=datetime(2026, 9, 20, tzinfo=timezone.utc),
)
assert 0 <= status["geopolitical_escalation_index"] <= 100
assert status["model_boundary"]["changes_stage_0_4"] is False
assert status["model_boundary"]["changes_financial_crisis_score"] is False
assert status["counts"]["events"] == 3
assert any(x["actor"] == "Russia" for x in status["campaigns"])

print(json.dumps({
    "event_scores": [x["geopolitical_event_score"] for x in rows],
    "index": status["geopolitical_escalation_index"],
    "campaigns": status["campaigns"],
}, ensure_ascii=False))
