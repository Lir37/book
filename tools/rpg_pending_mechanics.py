#!/usr/bin/env python3
"""RPG v0.9: UNAPPROVED cap-change scenarios and candidate eligibility.

Approved baseline mana arithmetic lives in rpg_resource_model.py.
This module neither grants skills nor canonizes cap adjustments.
"""
from __future__ import annotations
from fractions import Fraction
from rpg_resource_model import canonical_human_regen_rate, effective_regen_rate

def candidate_mana_after_cap_change(old_max: int | Fraction,
                                    current: int | Fraction,
                                    new_max: int | Fraction,
                                    policy: str) -> Fraction:
    """Explicit what-if: absolute, fraction, or grant_delta. NO default."""
    a, m, b = Fraction(old_max), Fraction(current), Fraction(new_max)
    if a <= 0 or b <= 0 or not 0 <= m <= a:
        raise ValueError("Invalid max mana or current mana")
    if policy == "preserve_absolute":
        return min(b, m)
    if policy == "preserve_fraction":
        return min(b, m * b / a)
    if policy == "grant_delta":
        return max(Fraction(0), min(b, m + b - a))
    raise ValueError("Select a candidate policy explicitly; author approval pending")

def recovery_seconds_to_target(max_mana: int | Fraction,
                               current: int | Fraction,
                               target: int | Fraction, form: str,
                               multiplier: int | Fraction = 1) -> Fraction:
    """Pure canonical-rate calculation, NOT a claim about interruption in battle."""
    cap, m, goal, buff = map(Fraction, (max_mana, current, target, multiplier))
    if cap <= 0 or not 0 <= m <= cap or not 0 <= goal <= cap or buff <= 0:
        raise ValueError("Invalid recovery scenario")
    if not isinstance(form, str) or not form:
        raise ValueError("Form required")
    if goal <= m:
        return Fraction(0)
    rate = effective_regen_rate(canonical_human_regen_rate(cap), form) * buff
    return (goal - m) / rate

def candidate_skill_access(skill: dict, *, level: int, actor_class: str,
                           learned_ids: set[str], form: str = "human",
                           unlocked_forms: set[str] | None = None,
                           specialization_confirmed: bool = False) -> bool:
    """Possible use AFTER separate learning; proposal gates are conservative.

    A skill availability check never teaches skills or unlocks beast forms.
    Level>=30 specialization gate is PROPOSAL only, not canonical.
    """
    if not isinstance(level, int) or not 1 <= level <= 100:
        raise ValueError("Level outside 1..100")
    if not isinstance(learned_ids, set):
        raise TypeError("Explicit learned set required")
    branch = skill["branch"]
    owner = "druid" if branch.startswith("druid_") else branch
    if actor_class != owner or skill["id"] not in learned_ids:
        return False
    if level < skill["level_gate"] or skill.get("automatic_unlock") is not False:
        return False
    if skill["category"] == "form_unlock_proposal":
        return False
    if skill["level_gate"] >= 30 and not specialization_confirmed:
        return False
    if skill["access"] == "human_only":
        return form == "human"
    if skill["access"] == "beast_only_when_unlocked":
        return bool(form != "human" and unlocked_forms and form in unlocked_forms)
    if owner != "druid":
        return True
    return False
