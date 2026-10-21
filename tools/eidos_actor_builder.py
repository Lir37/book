#!/usr/bin/env python3
"""Conservative canonical 6x6 Eidos NPC/hero validator.

This is a validation tool, not an automatic skill grant or a source of story facts.
It does not simulate combat, determine motives, or generate characters into the novel.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FILES = (
    "RPG_ЭЙДОС_АРКАНУМ_114_НАВЫКОВ_v1.4_2026-10-21.json",
    "RPG_ЭЙДОС_ПРОТОКОЛ_109_НАВЫКОВ_v1.4_2026-10-21.json",
)
ROSTER = "RPG_ЭЙДОС_ТЕСТОВЫЕ_СБОРКИ_48_6x6_v1.3_2026-10-21.json"
LEGACY = "RPG_ЭЙДОС_УТВЕРЖДЁННЫЙ_КАТАЛОГ_140_НАВЫКОВ_v1.0_2026-10-21.json"
STATS = ("Сила", "Ловкость", "Выносливость", "Живучесть", "Восприятие", "Дух")

def read_data(root: Path = ROOT) -> dict[str, Any]:
    roster = json.loads((root / ROSTER).read_text(encoding="utf-8"))["selectable_classes"]
    new = [x for name in FILES for x in json.loads((root / name).read_text(encoding="utf-8"))["entries"]]
    old = json.loads((root / LEGACY).read_text(encoding="utf-8"))["records"]
    return {"roster": roster, "new": {s["id"]: s for s in new}, "legacy": {s["id"]: s for s in old}}

def validate_actor(actor: dict[str, Any], data: dict[str, Any]) -> list[str]:
    """Validate only facts proven by the catalogs, not imagined training or mechanics."""
    issues: list[str] = []
    faction, cls, level = actor.get("faction"), actor.get("class_id"), actor.get("level")
    roster = data["roster"]
    if faction not in roster:
        return ["Unknown faction"]
    if cls is not None and cls not in roster[faction]:
        issues.append("Unknown or forbidden player class")
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 100:
        return issues + ["Level must be an integer from 1 to 100"]
    spec = actor.get("specialization")
    if spec is not None:
        if cls is None or spec not in roster[faction].get(cls, {}).get("specializations", []):
            issues.append("Specialization not available to this class")
        if level < 20:
            issues.append("Cannot specialize before level 20")
    if cls is None and spec is not None:
        issues.append("No specialization without base class")
    stats = actor.get("attributes")
    if not isinstance(stats, dict) or set(stats) != set(STATS):
        issues.append("Exactly the six canonical attributes are required")
    elif any(not isinstance(v, int) or isinstance(v, bool) or v < 1 for v in stats.values()):
        issues.append("All six attributes must be positive integers")
    learned = actor.get("learned_skill_ids", [])
    if not isinstance(learned, list) or any(not isinstance(x, str) for x in learned) or len(learned) != len(set(learned)):
        return issues + ["learned_skill_ids must contain unique strings"]
    evidence = actor.get("training_evidence", {})
    if not isinstance(evidence, dict):
        return issues + ["training_evidence must be an object keyed by learned skill IDs"]
    for sid in learned:
        item = data["new"].get(sid)
        legacy = data["legacy"].get(sid)
        if item is None and legacy is None:
            issues.append(f"Unknown skill: {sid}")
            continue
        if not isinstance(evidence.get(sid), str) or not evidence[sid].strip():
            issues.append(f"Missing training evidence: {sid}")
        if item is not None:
            if item["faction"] != faction or item["class_id"] != cls:
                issues.append(f"Wrong class/faction for skill: {sid}")
            if item["specialization"] is not None and item["specialization"] != spec:
                issues.append(f"Wrong specialization for skill: {sid}")
            if level < item["level_gate"]:
                issues.append(f"Insufficient level for skill: {sid}")
            for required in item["prerequisites"]:
                if required not in learned:
                    issues.append(f"Missing prerequisite {required} for {sid}")
        else:
            if level < legacy["level_gate"]:
                issues.append(f"Insufficient level for legacy skill: {sid}")
            # Legacy eligibility is specialized and cannot be inferred from class alone.
            # Explicit author confirmation of compatibility is needed for NPC construction.
            approval = actor.get("legacy_access_evidence", {}).get(sid)
            if not isinstance(approval, str) or not approval.strip():
                issues.append(f"Missing specific legacy access proof: {sid}")
    if faction == "protocol" and actor.get("tech_mana", 0):
        issues.append("Protocol has no universal technomana")
    return issues

def usable_now(actor: dict[str, Any], skill_id: str, data: dict[str, Any]) -> tuple[bool, str]:
    if skill_id not in actor.get("learned_skill_ids", []) or validate_actor(actor, data):
        return False, "Not learned with all requirements, or actor invalid"
    skill = data["new"].get(skill_id)
    if skill is None:
        return False, "Legacy usability needs its individual canonical record"
    if actor.get("incapacitated") or actor.get("equipment_ready") is False:
        return False, "Injury, missing equipment or lack of access"
    res = skill["resource"]
    if res["kind"] == "mana":
        M = 50 + 5 * actor["attributes"]["Дух"] + 2 * (actor["level"] - 1)
        needed = math.ceil(M * res["percent_max"] / 100)
        if res.get("human_only") and actor.get("form", "human") != "human":
            return False, "Druid magic is human-only"
        if actor.get("mana_current", 0) < needed:
            return False, f"Insufficient mana (requires {needed})"
    if res["kind"] == "physiology":
        current_form = actor.get("form", "human")
        mastered = actor.get("known_beast_forms", [])
        if current_form == "human" or current_form not in mastered:
            return False, "Requires being in a separately learned, currently active beast form"
    if res["kind"] in ("physical", "materials", "physiology") and not actor.get("physical_conditions_ready", False):
        return False, "Physical requirements not yet confirmed"
    return True, "Eligible for attempt, not guaranteed success"

def main() -> int:
    p = argparse.ArgumentParser(description="Validate an Eidos actor; do not mint skills.")
    p.add_argument("actor_json", type=Path)
    args = p.parse_args()
    actor = json.loads(args.actor_json.read_text(encoding="utf-8"))
    issues = validate_actor(actor, read_data())
    print(json.dumps({"valid": not issues, "issues": issues}, ensure_ascii=False, indent=2))
    return int(bool(issues))

if __name__ == "__main__":
    raise SystemExit(main())
