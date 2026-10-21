#!/usr/bin/env python3
"""Eidos v0.8 approved mana ledger plus explicitly selected what-if modes.

Defaults: one paid entry ceil(20% max) or ceil(14% with Balance);
free beast upkeep/return; human restores full cap in 600 in-game
seconds, beast in 2400. Fractional recovery accumulates exactly.
Exposing override parameters permits counterfactual tests but does
not change the canonical DEFAULT.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Iterable
from rpg_transition_contract import HUMAN, NotEnoughMana, transition_cost, proportional_entry_cost
from rpg_resource_model import regenerated_mana, canonical_human_regen_rate


class FormActionUnavailable(ValueError):
    """A druid spell or active item is unavailable in the current anatomy."""

def trace_mana(max_mana: int | Fraction, initial_mana: int | Fraction,
               actions: Iterable[tuple[str, object]],
               entry_cost: int | Fraction | None = None,
               balance_of_chimeras: bool = False,
               human_regen_per_second: int | Fraction | None = None,
               rounding_mode: str = "ceil",
               regen_multiplier: int | Fraction = 1) -> tuple[str, Fraction, tuple[tuple[str, Fraction], ...]]:
    """Run actions, preserving exact fractional mana for project comparisons.

    Actions: form (unlocked beast or human), cast (human druid spell),
    restore (human item/potion), form_skill (beast-specific action),
    regen (hypothetical explicitly supplied mana gain), hold (duration).
    On hold: default M/600 for human and M/2400 for beast per game second.
    A supplied rate overrides that for what-if comparison; supply 0 only
    for explicit zero-recovery tests. Regen multiplier permits faction +10%
    while maintaining 1:4. Form upkeep always costs ZERO mana.
    Billed form entry is ceil of final discounted raw cost, by default.
    Skill unlocks, physical injuries, cooldowns and consciousness are external.
    """
    ceiling, mana = Fraction(max_mana), Fraction(initial_mana)
    if ceiling <= 0 or not 0 <= mana <= ceiling:
        raise ValueError("Mana cap must be positive; starting mana must be within cap")
    base_entry = proportional_entry_cost(ceiling) if entry_cost is None else Fraction(entry_cost)
    if base_entry <= 0:
        raise ValueError("Paid form entry base must be positive")
    rate = (canonical_human_regen_rate(ceiling) if human_regen_per_second is None
            else Fraction(human_regen_per_second))
    multiplier = Fraction(regen_multiplier)
    if rate < 0 or multiplier <= 0:
        raise ValueError("Recovery rate cannot be negative; multiplier must be positive")
    if rounding_mode not in ("ceil", "exact", "half_up"):
        raise ValueError("Unsupported mana entry rounding")
    body, ledger = HUMAN, []
    for action, arg in actions:
        if action == "form":
            if not isinstance(arg, str):
                raise ValueError("Target form must be a name")
            raw_price = transition_cost(body, arg, base_entry, balance_of_chimeras)
            if rounding_mode == "exact":
                price = raw_price
            elif rounding_mode == "ceil":
                price = Fraction((raw_price.numerator + raw_price.denominator - 1)
                                 // raw_price.denominator)
            else:
                price = Fraction((2 * raw_price.numerator + raw_price.denominator)
                                 // (2 * raw_price.denominator))
            if mana < price:
                raise NotEnoughMana(f"Target {arg} costs {price} with only {mana} available")
            mana -= price
            body = arg
        elif action == "cast":
            if body != HUMAN:
                raise FormActionUnavailable("General druid magic requires a human body")
            price = Fraction(arg)
            if price <= 0:
                raise ValueError("Spell price must be positive")
            if mana < price:
                raise NotEnoughMana(f"Spell costs {price} with only {mana} available")
            mana -= price
        elif action == "restore":
            if body != HUMAN:
                raise FormActionUnavailable("Items and potions require human hands")
            amount = Fraction(arg)
            if amount <= 0:
                raise ValueError("Restore amount must be positive")
            mana = min(ceiling, mana + amount)
        elif action == "form_skill":
            if body == HUMAN:
                raise FormActionUnavailable("Form-specific skills require the beast body")
            price = Fraction(arg)
            if price < 0:
                raise ValueError("Form skill cost cannot be negative")
            if mana < price:
                raise NotEnoughMana(f"Form skill costs {price} with only {mana} available")
            mana -= price
        elif action == "regen":
            # Explicit hypothetical restoration, NOT automatic canon regeneration.
            amount = Fraction(arg)
            if amount <= 0:
                raise ValueError("Regeneration scenario amount must be positive")
            mana = min(ceiling, mana + amount)
        elif action == "hold":
            duration = Fraction(arg)
            if duration < 0:
                raise ValueError("Duration cannot be negative")
            if rate > 0:
                mana = regenerated_mana(ceiling, mana, duration, rate * multiplier, body)
            # Zero-cost form upkeep; rate 0 exists only for explicit test override.
        else:
            raise ValueError(f"Unknown action {action!r}")
        ledger.append((body, mana))
    return body, mana, tuple(ledger)


def compare_percentage_scenarios(cap: int | Fraction = 125) -> tuple[dict, ...]:
    """Historical 5/10/15% counterfactuals plus approved 20%, no rounding."""
    reserve = Fraction(cap)
    scenarios = []
    for fraction in (Fraction(1, 20), Fraction(1, 10),
                     Fraction(3, 20), Fraction(1, 5)):
        price = reserve * fraction
        without = trace_mana(reserve, reserve,
                             (("form", "fellur"), ("form", HUMAN),
                              ("form", "fellur")), price, False,
                             human_regen_per_second=0, rounding_mode="exact")
        with_skill = trace_mana(reserve, reserve,
                                (("form", "fellur"), ("form", HUMAN),
                                 ("form", "fellur")), price, True,
                                human_regen_per_second=0, rounding_mode="exact")
        scenarios.append({"fraction": fraction, "price": price,
                          "after_two_entries": without[1],
                          "after_two_discounted_entries": with_skill[1]})
    return tuple(scenarios)


if __name__ == "__main__":
    for result in compare_percentage_scenarios():
        print("Project-only entry price:", result)
