#!/usr/bin/env python3
"""Geopolitical / hybrid-threat enrichment for the crisis-watch news layer.

Design principle:
- event facts, actor mentions and reported attribution are separate fields;
- an allegation in a headline is never silently converted into a confirmed fact;
- the escalation index is a state indicator, not a probability of war;
- geopolitical signals are report-only and do not change Stage 0-4.
"""
from __future__ import annotations

import json
import math
import pathlib
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_TAXONOMY = ROOT / "data" / "geopolitical_taxonomy.json"

PHYSICAL_MODALITIES = {
    "sabotage", "explosive_drone", "drone_incursion", "airspace_violation",
    "missile_incursion", "arson", "infrastructure_interference",
    "assassination_plot",
}
CRITICAL_TARGETS = {
    "critical_infrastructure", "energy", "transport", "military_logistics",
    "military_facility", "civil_aviation", "undersea_infrastructure",
    "communications", "government",
}
MILITARY_RESPONSES = {"air_intercept", "military_alert"}
DIPLOMATIC_RESPONSES = {
    "sanctions", "diplomatic_expulsion", "consulate_closure",
    "collective_statement",
}
EUROPEAN_TARGET_ACTORS = {
    "Germany", "Poland", "Romania", "France", "United Kingdom", "EU", "NATO",
}
OFFICIAL_PUBLISHER_MARKERS = (
    "NATO", "Council of the EU", "European Council", "European Commission",
    "Bundesregierung", "Federal Government", "Ministry", "Government",
)


def load_taxonomy(path: pathlib.Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_TAXONOMY
    return json.loads(path.read_text(encoding="utf-8"))


def _text(article: dict[str, Any]) -> str:
    return " ".join([
        str(article.get("title") or ""),
        str(article.get("summary") or ""),
    ]).lower()


def _alias_positions(text: str, alias: str) -> list[int]:
    alias_l = str(alias).lower()
    compact = re.sub(r"[^a-z0-9]", "", alias_l)
    if compact and len(compact) <= 3 and re.fullmatch(r"[a-z0-9.]+", alias_l):
        pattern = re.compile(
            r"(?<![a-z0-9])" + re.escape(alias_l) + r"(?![a-z0-9])"
        )
        return [m.start() for m in pattern.finditer(text)]
    out = []
    start = 0
    while True:
        pos = text.find(alias_l, start)
        if pos < 0:
            break
        out.append(pos)
        start = pos + max(1, len(alias_l))
    return out


def _matches(text: str, mapping: dict[str, list[str]]) -> list[str]:
    out = []
    for key, aliases in mapping.items():
        if any(_alias_positions(text, str(alias)) for alias in aliases):
            out.append(key)
    return sorted(set(out))


def _has_any(text: str, values: list[str]) -> bool:
    return any(str(v).lower() in text for v in values)


def _source_class(article: dict[str, Any]) -> str:
    publisher = str(article.get("publisher") or article.get("source_name") or "")
    if any(marker.lower() in publisher.lower() for marker in OFFICIAL_PUBLISHER_MARKERS):
        return "official_primary"
    if str(article.get("query_theme") or "").startswith(("nato_", "eu_")):
        return "official_discovery_query"
    return "news_report"


def _actor_positions(text: str, actor_map: dict[str, list[str]]) -> list[tuple[int, str]]:
    positions = []
    for actor, aliases in actor_map.items():
        for alias in aliases:
            for pos in _alias_positions(text, str(alias)):
                positions.append((pos, actor))
    return sorted(set(positions))


def _nearest_actor(
    text: str,
    actor_positions: list[tuple[int, str]],
    cue: str,
    *,
    max_distance: int = 100,
) -> list[str]:
    cue_l = str(cue).lower()
    found = []
    start = 0
    while True:
        pos = text.find(cue_l, start)
        if pos < 0:
            break
        distances = sorted(
            (abs(actor_pos - pos), actor)
            for actor_pos, actor in actor_positions
            if abs(actor_pos - pos) <= max_distance
        )
        if distances:
            best = distances[0][0]
            found.extend(actor for dist, actor in distances if dist == best)
        start = pos + max(1, len(cue_l))
    return sorted(set(found))


def _reported_attributions(
    text: str,
    actors: list[str],
    taxonomy: dict[str, Any],
) -> list[dict[str, str]]:
    if not actors:
        return []

    attr = taxonomy.get("attribution", {})
    actor_map = {
        actor: taxonomy.get("actors", {}).get(actor, [actor])
        for actor in actors
    }
    positions = _actor_positions(text, actor_map)

    attributed = set()
    suspected = set()
    disputed = set()

    for cue in attr.get("attributed_cues", []):
        attributed.update(_nearest_actor(text, positions, cue))
    for cue in attr.get("suspected_cues", []):
        suspected.update(_nearest_actor(text, positions, cue))
    for cue in attr.get("dispute_cues", []):
        disputed.update(_nearest_actor(text, positions, cue))

    results = []
    for actor in sorted(attributed | suspected):
        if actor in attributed and actor in disputed:
            status = "reported_attribution_disputed"
        elif actor in attributed:
            status = "reported_attributed"
        else:
            status = "suspected"
        results.append({"actor": actor, "status": status})
    return results


def _transmission_indicators(
    modalities: list[str],
    targets: list[str],
    taxonomy: dict[str, Any],
) -> list[str]:
    mapping = taxonomy.get("market_transmission", {})
    values = set()
    for item in [*modalities, *targets]:
        values.update(mapping.get(item, []))
    return sorted(values)


def _severity(dimensions: dict[str, bool], modalities: list[str], responses: list[str]) -> float:
    score = 0.0
    score += 18.0 if dimensions["physical_attack"] else 0.0
    score += 16.0 if dimensions["critical_infrastructure"] else 0.0
    score += 12.0 if dimensions["alliance_proximity"] else 0.0
    score += 10.0 if dimensions["cross_border"] else 0.0
    score += 12.0 if dimensions["reported_attribution"] else 0.0
    score += 10.0 if dimensions["military_response"] else 0.0
    score += 8.0 if dimensions["diplomatic_response"] else 0.0
    score += 14.0 if dimensions["explicit_threat"] else 0.0
    # Cyber/information/economic pressure can matter even without physical attack.
    if "cyber_attack" in modalities:
        score += 8.0
    if "information_operation" in modalities:
        score += 4.0
    if "economic_coercion" in modalities:
        score += 6.0
    return round(min(100.0, score), 1)


def enrich_geopolitical_articles(
    rows: list[dict[str, Any]],
    taxonomy: dict[str, Any],
) -> None:
    actor_map = taxonomy.get("actors", {})
    modality_map = taxonomy.get("modalities", {})
    target_map = taxonomy.get("targets", {})
    response_map = taxonomy.get("responses", {})

    for article in rows:
        text = _text(article)
        actors = _matches(text, actor_map)
        modalities = _matches(text, modality_map)
        targets = _matches(text, target_map)
        responses = _matches(text, response_map)
        attributions = _reported_attributions(text, actors, taxonomy)

        query_theme = str(article.get("query_theme") or "")
        geopolitical = bool(
            modalities or targets or responses or attributions
            or query_theme.startswith(("geopolitics_", "nato_", "eu_"))
        )

        dims = {
            "physical_attack": bool(set(modalities) & PHYSICAL_MODALITIES),
            "critical_infrastructure": bool(set(targets) & CRITICAL_TARGETS),
            "alliance_proximity": bool(
                "NATO" in actors
                or bool(set(actors) & EUROPEAN_TARGET_ACTORS)
                or "military_logistics" in targets
                or "military_facility" in targets
            ),
            "cross_border": (
                len(set(actors) & EUROPEAN_TARGET_ACTORS) >= 2
                or any(x in text for x in ("cross-border", "across europe", "border", "国境", "欧州各国"))
            ),
            "reported_attribution": any(
                x["status"] in {"reported_attributed", "reported_attribution_disputed"}
                for x in attributions
            ),
            "military_response": bool(set(responses) & MILITARY_RESPONSES),
            "diplomatic_response": bool(set(responses) & DIPLOMATIC_RESPONSES),
            "explicit_threat": "military_threat" in modalities,
        }

        if not geopolitical:
            article["geopolitical"] = False
            continue

        article["geopolitical"] = True
        article["geopolitical_source_class"] = _source_class(article)
        article["geopolitical_actors"] = actors
        article["geopolitical_modalities"] = modalities
        article["geopolitical_targets"] = targets
        article["geopolitical_responses"] = responses
        article["reported_attributions"] = attributions
        article["geopolitical_dimensions"] = dims
        article["market_transmission_candidates"] = _transmission_indicators(
            modalities, targets, taxonomy
        )
        article["geopolitical_event_score"] = _severity(dims, modalities, responses)


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def build_geopolitical_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: dict[str, dict[str, Any]] = {}
    for article in rows:
        if not article.get("geopolitical"):
            continue
        eid = str(article.get("event_id") or article.get("doc_id") or "")
        if not eid:
            continue
        event = events.setdefault(eid, {
            "event_id": eid,
            "label": article.get("event_label") or article.get("title"),
            "first_seen": article.get("published_at"),
            "last_seen": article.get("published_at"),
            "article_count": 0,
            "publishers": set(),
            "actors": set(),
            "modalities": set(),
            "targets": set(),
            "responses": set(),
            "reported_attributions": {},
            "dimensions": defaultdict(bool),
            "market_transmission_candidates": set(),
            "max_event_score": 0.0,
        })
        event["article_count"] += 1
        if article.get("publisher"):
            event["publishers"].add(article["publisher"])
        event["actors"].update(article.get("geopolitical_actors") or [])
        event["modalities"].update(article.get("geopolitical_modalities") or [])
        event["targets"].update(article.get("geopolitical_targets") or [])
        event["responses"].update(article.get("geopolitical_responses") or [])
        event["market_transmission_candidates"].update(
            article.get("market_transmission_candidates") or []
        )
        for a in article.get("reported_attributions") or []:
            actor = a.get("actor")
            status = a.get("status")
            if actor and status:
                previous = event["reported_attributions"].get(actor)
                priority = {
                    "suspected": 1,
                    "reported_attributed": 2,
                    "reported_attribution_disputed": 3,
                }
                if previous is None or priority.get(status, 0) > priority.get(previous, 0):
                    event["reported_attributions"][actor] = status
        for key, value in (article.get("geopolitical_dimensions") or {}).items():
            event["dimensions"][key] = bool(event["dimensions"][key] or value)
        event["max_event_score"] = max(
            event["max_event_score"],
            float(article.get("geopolitical_event_score") or 0.0),
        )
        dt = article.get("published_at")
        if dt and (not event["first_seen"] or dt < event["first_seen"]):
            event["first_seen"] = dt
        if dt and (not event["last_seen"] or dt > event["last_seen"]):
            event["last_seen"] = dt

    out = []
    for e in events.values():
        out.append({
            "event_id": e["event_id"],
            "label": e["label"],
            "first_seen": e["first_seen"],
            "last_seen": e["last_seen"],
            "article_count": e["article_count"],
            "publisher_count": len(e["publishers"]),
            "actors": sorted(e["actors"]),
            "modalities": sorted(e["modalities"]),
            "targets": sorted(e["targets"]),
            "responses": sorted(e["responses"]),
            "reported_attributions": [
                {"actor": actor, "status": status}
                for actor, status in sorted(e["reported_attributions"].items())
            ],
            "dimensions": dict(e["dimensions"]),
            "market_transmission_candidates": sorted(e["market_transmission_candidates"]),
            "event_score": round(e["max_event_score"], 1),
        })
    return sorted(out, key=lambda x: (x.get("first_seen") or "", x["event_id"]))


def build_geopolitical_timeseries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events = build_geopolitical_events(rows)
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}

    def add(day: str, kind: str, key: str, event: dict[str, Any]) -> None:
        b = buckets.setdefault((day, kind, key), {
            "day": day,
            "kind": kind,
            "key": key,
            "events": set(),
            "physical_events": 0,
            "critical_infrastructure_events": 0,
            "attributed_events": 0,
            "military_response_events": 0,
            "explicit_threat_events": 0,
            "severity_sum": 0.0,
            "max_severity": 0.0,
        })
        if event["event_id"] in b["events"]:
            return
        b["events"].add(event["event_id"])
        d = event.get("dimensions") or {}
        b["physical_events"] += int(bool(d.get("physical_attack")))
        b["critical_infrastructure_events"] += int(bool(d.get("critical_infrastructure")))
        b["attributed_events"] += int(bool(d.get("reported_attribution")))
        b["military_response_events"] += int(bool(d.get("military_response")))
        b["explicit_threat_events"] += int(bool(d.get("explicit_threat")))
        b["severity_sum"] += float(event.get("event_score") or 0.0)
        b["max_severity"] = max(b["max_severity"], float(event.get("event_score") or 0.0))

    for event in events:
        day = str(event.get("first_seen") or "")[:10]
        if not day:
            continue
        add(day, "overall", "geopolitical_hybrid", event)
        for actor in event.get("actors") or []:
            add(day, "actor_mention", actor, event)
        for a in event.get("reported_attributions") or []:
            if a.get("actor"):
                add(day, "reported_attribution", a["actor"], event)
        for modality in event.get("modalities") or []:
            add(day, "modality", modality, event)
        for target in event.get("targets") or []:
            add(day, "target", target, event)

    out = []
    for b in buckets.values():
        n = len(b["events"])
        out.append({
            "day": b["day"],
            "kind": b["kind"],
            "key": b["key"],
            "event_count": n,
            "physical_events": b["physical_events"],
            "critical_infrastructure_events": b["critical_infrastructure_events"],
            "attributed_events": b["attributed_events"],
            "military_response_events": b["military_response_events"],
            "explicit_threat_events": b["explicit_threat_events"],
            "avg_event_score": round(b["severity_sum"] / max(1, n), 2),
            "max_event_score": round(b["max_severity"], 2),
        })
    return sorted(out, key=lambda x: (x["day"], x["kind"], x["key"]))


def _top_quartile_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    values = sorted(values, reverse=True)
    n = max(1, math.ceil(len(values) * 0.25))
    return sum(values[:n]) / n


def build_geopolitical_status(
    rows: list[dict[str, Any]],
    *,
    window_days: int = 90,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    events = build_geopolitical_events(rows)
    if as_of is None:
        dates = [_parse_dt(e.get("last_seen")) for e in events]
        as_of = max(dates) if dates else datetime.now(timezone.utc)
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)

    start = as_of - timedelta(days=window_days)
    selected = [e for e in events if _parse_dt(e.get("last_seen")) >= start]
    recent30 = [e for e in selected if _parse_dt(e.get("last_seen")) >= as_of - timedelta(days=30)]
    prev30 = [
        e for e in selected
        if as_of - timedelta(days=60) <= _parse_dt(e.get("last_seen")) < as_of - timedelta(days=30)
    ]

    event_scores = [float(e.get("event_score") or 0.0) for e in selected]
    severity = _top_quartile_mean(event_scores)
    density = min(100.0, len(selected) / 20.0 * 100.0)

    countries = set()
    for e in selected:
        countries.update(set(e.get("actors") or []) & EUROPEAN_TARGET_ACTORS)
    breadth = min(100.0, len(countries) / 5.0 * 100.0)

    response_events = sum(
        bool((e.get("dimensions") or {}).get("military_response"))
        or bool((e.get("dimensions") or {}).get("diplomatic_response"))
        for e in selected
    )
    response = min(100.0, response_events / 8.0 * 100.0)

    if not prev30:
        momentum = 100.0 if recent30 else 0.0
    else:
        ratio = len(recent30) / len(prev30)
        momentum = max(0.0, min(100.0, 50.0 + 50.0 * (ratio - 1.0)))

    index = (
        0.30 * severity
        + 0.20 * density
        + 0.15 * breadth
        + 0.15 * response
        + 0.20 * momentum
    )

    attribution_threads: dict[str, list[dict[str, Any]]] = defaultdict(list)
    disputed = 0
    unattributed = 0
    for e in selected:
        attrs = e.get("reported_attributions") or []
        if not attrs:
            unattributed += 1
        for a in attrs:
            actor = a.get("actor")
            status = a.get("status")
            if actor:
                attribution_threads[actor].append(e)
            if status == "reported_attribution_disputed":
                disputed += 1

    campaigns = []
    for actor, actor_events in attribution_threads.items():
        actor_events = sorted(actor_events, key=lambda x: x.get("last_seen") or "")
        campaigns.append({
            "actor": actor,
            "event_count": len({x["event_id"] for x in actor_events}),
            "first_seen": actor_events[0].get("first_seen"),
            "last_seen": actor_events[-1].get("last_seen"),
            "max_event_score": max(float(x.get("event_score") or 0.0) for x in actor_events),
            "modalities": sorted({m for x in actor_events for m in x.get("modalities") or []}),
            "targets": sorted({t for x in actor_events for t in x.get("targets") or []}),
            "responses": sorted({r for x in actor_events for r in x.get("responses") or []}),
        })
    campaigns.sort(key=lambda x: (x["event_count"], x["max_event_score"]), reverse=True)

    return {
        "version": 1,
        "as_of": as_of.isoformat().replace("+00:00", "Z"),
        "window_days": window_days,
        "geopolitical_escalation_index": round(index, 1),
        "interpretation": "state index only; not a probability of war or attribution confidence",
        "components": {
            "top_quartile_event_severity": round(severity, 1),
            "event_density": round(density, 1),
            "cross_border_breadth": round(breadth, 1),
            "response_intensity": round(response, 1),
            "thirty_day_momentum": round(momentum, 1),
        },
        "counts": {
            "events": len(selected),
            "recent_30d_events": len(recent30),
            "previous_30d_events": len(prev30),
            "physical_events": sum(bool((e.get("dimensions") or {}).get("physical_attack")) for e in selected),
            "critical_infrastructure_events": sum(bool((e.get("dimensions") or {}).get("critical_infrastructure")) for e in selected),
            "reported_attribution_events": sum(bool((e.get("dimensions") or {}).get("reported_attribution")) for e in selected),
            "unattributed_events": unattributed,
            "disputed_attribution_records": disputed,
            "military_response_events": sum(bool((e.get("dimensions") or {}).get("military_response")) for e in selected),
            "explicit_threat_events": sum(bool((e.get("dimensions") or {}).get("explicit_threat")) for e in selected),
        },
        "campaigns": campaigns[:10],
        "market_transmission_candidates": sorted({
            i for e in selected for i in e.get("market_transmission_candidates") or []
        }),
        "model_boundary": {
            "changes_stage_0_4": False,
            "changes_financial_crisis_score": False,
            "reason": "Geopolitical text signals remain observational until enough history exists for out-of-sample validation.",
        },
    }
