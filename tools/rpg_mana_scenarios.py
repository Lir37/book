#!/usr/bin/env python3
"""What-if Eidos mana ledger. NOT a source of canonical RPG prices.

Canon: beast entry costs a positive amount, beast upkeep and voluntary return
to human cost ZERO, and Balance of Chimeras reduces paid transitions by 30%.
Mana cap, actual entry prices, rounding, regeneration, spell availability and
potion restoration values are UNKNOWN. Supply them as explicit scenario inputs.
This ledger deliberately assumes *no* regeneration unless a scenario inserts
an explicit 'restore' event. The assumption belongs to the test, not the book.
"""
from __future__ import annotations
from fractions import Fraction
from typing import Iterable
from rpg_transition_contract import HUMAN, NotEnoughMana, transition_cost

def trace_mana(max_mana: int | Fraction, initial_mana: int | Fraction,
               actions: Iterable[tuple[str, object]],
               entry_cost: int | Fraction,
               balance_of_chimeras: bool = False) -> tuple[str, Fraction, tuple[tuple[str, Fraction], ...]]:
    """Run actions, preserving exact fractional mana for project comparisons.

    Actions: ('form', 'fellur'/'human'/other open form), ('cast', positive mana),
    ('restore', positive mana as from an external potion), or ('hold', duration).
    Hold never spends mana; this makes the zero-upkeep rule executable. 
    Injury, anatomy, ability availability, cooldowns and consciousness are
    intentionally outside this mana-only ledger.
    """
    ceiling, mana = Fraction(max_mana), Fraction(initial_mana)
    if ceiling <= 0 or not 0 <= mana <= ceiling:
        raise ValueError("Mana cap must be positive; starting mana must be within cap")
    body, ledger = HUMAN, []
    for action, arg in actions:
        if action == "form":
            if not isinstance(arg, str):
                raise ValueError("Target form must be a name")
            price = transition_cost(body, arg, entry_cost, balance_of_chimeras)
            if mana < price:
                raise NotEnoughMana(f"Target {arg} costs {price} with only {mana} available")
            mana -= price
            body = arg
        elif action == "cast":
            price = Fraction(arg)
            if price <= 0:
                raise ValueError("Spell price must be positive")
            if mana < price:
                raise NotEnoughMana(f"Spell costs {price} with only {mana} available")
            mana -= price
        elif action == "restore":
            amount = Fraction(arg)
            if amount <= 0:
                raise ValueError("Restore amount must be positive")
            mana = min(ceiling, mana + amount)
        elif action == "hold":
            duration = Fraction(arg)
            if duration < 0:
                raise ValueError("Duration cannot be negative")
            # No upkeep. Optional regeneration is a separate explicit event.
        else:
            raise ValueError(f"Unknown action {action!r}")
        ledger.append((body, mana))
    return body, mana, tuple(ledger)


def compare_percentage_scenarios(cap: int | Fraction = 125) -> tuple[dict, ...]:
    """Four author-UNAPPROVED entry-price what-ifs at fully charged reserve."""
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
