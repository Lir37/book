#!/usr/bin/env python3
"""What-if Eidos mana ledger. NOT a source of canonical RPG prices.

Canon: 20% of calculated max mana on paid entry, minus 30% when unlocked;
no charge for holding a form or returning to human, including at zero mana.
General druid spells and active items require human anatomy. Only an
explicitly form-specific skill can be activated in an animal body.
Author-approved beast regeneration is 1/4 the human rate. Absolute human
rate, mana-cap formula, rounding and potion amount are unapproved.
When no positive human rate is provided, hold simulates a ZERO-REGEN TEST
scenario only; do not interpret the zero-rate diagnostic as game canon.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Iterable
from rpg_transition_contract import HUMAN, NotEnoughMana, transition_cost, proportional_entry_cost
from rpg_resource_model import regenerated_mana


class FormActionUnavailable(ValueError):
    """A druid spell or active item is unavailable in the current anatomy."""

def trace_mana(max_mana: int | Fraction, initial_mana: int | Fraction,
               actions: Iterable[tuple[str, object]],
               entry_cost: int | Fraction | None = None,
               balance_of_chimeras: bool = False,
               human_regen_per_second: int | Fraction | None = None) -> tuple[str, Fraction, tuple[tuple[str, Fraction], ...]]:
    """Run actions, preserving exact fractional mana for project comparisons.

    Actions: form (unlocked beast or human), cast (human druid spell),
    restore (human item/potion), form_skill (beast-specific action),
    regen (hypothetical explicitly supplied mana gain), hold (duration).
    On hold: if human_regen_per_second is supplied, a human gains that rate
    and any beast gains exactly one quarter of it. If omitted, this is the
    explicit NO-REGEN comparison scenario. Form upkeep is always zero.
    Skill unlocks, physical injuries, cooldowns and consciousness are external.
    """
    ceiling, mana = Fraction(max_mana), Fraction(initial_mana)
    if ceiling <= 0 or not 0 <= mana <= ceiling:
        raise ValueError("Mana cap must be positive; starting mana must be within cap")
    base_entry = proportional_entry_cost(ceiling) if entry_cost is None else Fraction(entry_cost)
    if human_regen_per_second is not None and Fraction(human_regen_per_second) <= 0:
        raise ValueError('A supplied human recovery rate must be positive')
    body, ledger = HUMAN, []
    for action, arg in actions:
        if action == "form":
            if not isinstance(arg, str):
                raise ValueError("Target form must be a name")
            price = transition_cost(body, arg, base_entry, balance_of_chimeras)
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
            if human_regen_per_second is not None:
                mana = regenerated_mana(ceiling, mana, duration,
                                        human_regen_per_second, body)
            # Always zero mana UPKEEP; recovery uses an explicit rate input.
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
                              ("form", "fellur")), price, False)
        with_skill = trace_mana(reserve, reserve,
                                (("form", "fellur"), ("form", HUMAN),
                                 ("form", "fellur")), price, True)
        scenarios.append({"fraction": fraction, "price": price,
                          "after_two_entries": without[1],
                          "after_two_discounted_entries": with_skill[1]})
    return tuple(scenarios)


if __name__ == "__main__":
    for result in compare_percentage_scenarios():
        print("Project-only entry price:", result)
