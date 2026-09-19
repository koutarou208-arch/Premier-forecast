#!/usr/bin/env python3
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import mcp_server as s

caps = s.get_search_capabilities(probe_embeddings=False)
assert caps["lexical_search"] is True

state = s.get_current_state()
assert state["version"] >= 6
assert state["systemic_stress_score"] is not None

repo = s.get_indicator("repo")
assert repo["found"]
assert repo["indicator"]["id"] == "funding_market"

bank = s.search_crisis_data("銀行", 5)
assert bank["count"] >= 1

hist = s.search_history(limit=3)
assert hist["count"] >= 1

nn = s.get_neural_state()
assert nn["available"]
assert nn["version"] == 6

agent = s.get_self_improvement_state()
assert agent["available"]
assert agent["decision"] in {"accepted", "reject_all", "disabled"}

print(json.dumps({
    "current": state["systemic_stress_score"],
    "repo": repo["indicator"]["value"],
    "bank_results": bank["count"],
    "history_results": hist["count"],
    "nn": nn["current"]["production_nn_score"],
    "agent_decision": agent["decision"],
}, ensure_ascii=False))
