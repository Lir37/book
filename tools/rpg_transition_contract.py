#!/usr/bin/env python3
"""Symbolic regression model for the approved Eidos shapeshift rules.

The approved entry rule is proportional to maximum mana:
- beast form upkeep is free;
- every voluntary beast-to-human return costs zero mana, even at zero mana;
- every paid entry into a beast form costs 20% of calculated maximum mana;
- Balance of Chimeras reduces positive transition costs by 30%.

The formula for maximum mana, fractional/integer rounding, regeneration,
injury and unconsciousness rules are still open. Legacy entry_cost remains
available for explicit counterfactual 15% and other tests.
"""

from fractions import Fraction

HUMAN = "human"
APPROVED_ENTRY_FRACTION = Fraction(1, 5)  # author-approved 20%


class NotEnoughMana(ValueError):
    """A paid transformation was requested without sufficient mana."""


def transition_cost(source: str, target: str, entry_cost: int | Fraction,
                    balance_of_chimeras: bool = False) -> Fraction:
    """Return mana cost of a specific transition as an exact rational number.

    entry_cost is a PROJECT input for paid entries, not a universal RPG rule.
    The zero-cost return is independent of input prices, skills and mana.
    """
    if not source or not target:
        raise ValueError("Source and target form names cannot be blank")
    price = Fraction(entry_cost)
    if price < 0:
        raise ValueError("Entry cost cannot be negative")
    if target == HUMAN or source == target:
        return Fraction(0)
    if price <= 0:
        raise ValueError("Entry into a different beast form must have a paid cost")
    return price * (Fraction(7, 10) if balance_of_chimeras else Fraction(1))


def proportional_entry_cost(max_mana: int | Fraction,
                            balance_of_chimeras: bool = False) -> Fraction:
    """Approved 20% of maximum, minus 30% if Balance of Chimeras applies.

    Exact rational arithmetic avoids silently deciding integer rounding.
    """
    cap = Fraction(max_mana)
    if cap <= 0:
        raise ValueError("Calculated maximum mana must be positive")
    return cap * APPROVED_ENTRY_FRACTION * (
        Fraction(7, 10) if balance_of_chimeras else Fraction(1)
    )


def mana_after(source: str, target: str, mana: int | Fraction,
               entry_cost: int | Fraction,
               balance_of_chimeras: bool = False) -> Fraction:
    """Evaluate the mana balance, not injury, time, cooldown or permission."""
    current = Fraction(mana)
    if current < 0:
        raise ValueError("Mana cannot be negative")
    price = transition_cost(source, target, entry_cost, balance_of_chimeras)
    if price > current:
        raise NotEnoughMana(f"Requires {price}, available {current}")
    return current - price
