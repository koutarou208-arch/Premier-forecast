#!/usr/bin/env python3
import json
import os
import pathlib
import sys

os.environ["MCP_EMBEDDINGS"] = "on"
os.environ.setdefault(
    "MCP_EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mcp_server as s

caps = s.get_search_capabilities(probe_embeddings=True)
assert caps["embedding_model_loaded"] is True, caps

cases = [
    ("短期の資金調達が詰まり始めている兆候", {"funding_market", "banking_stress", "rates_liquidity"}),
    ("AI向けデータセンター融資の悪化", {"data_center", "private_credit", "bank_ai"}),
    ("原油高とエネルギー価格ショック", {"energy"}),
]

report = []
for query, expected in cases:
    result = s.semantic_search_crisis_data(query, limit=6)
    assert result["search_mode"] == "hybrid", result
    keys = [str(x.get("key")) for x in result["results"]]
    hit = next((k for k in keys if k in expected), None)
    assert hit is not None, {"query": query, "keys": keys, "expected": sorted(expected)}
    report.append({
        "query": query,
        "hit": hit,
        "top": [
            {
                "key": x.get("key"),
                "semantic_similarity": x.get("semantic_similarity"),
                "match_score": x.get("match_score"),
            }
            for x in result["results"][:3]
        ],
    })

cross = s.semantic_search_crisis_data(
    "banks are struggling to obtain short term funding",
    limit=6,
)
assert cross["search_mode"] == "hybrid"
cross_keys = [str(x.get("key")) for x in cross["results"]]
assert any(k in {"banking_stress", "funding_market"} for k in cross_keys)

print(json.dumps({
    "model": s.EMBEDDING_MODEL,
    "cases": report,
    "cross_language_top_keys": cross_keys[:6],
}, ensure_ascii=False))
