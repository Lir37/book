#!/usr/bin/env python3
"""Symbolic regression model for the approved Eidos shapeshift rules.

The approved entry rule is proportional to maximum mana:
- beast form upkeep is free;
- every voluntary beast-to-human return costs zero mana, even at zero mana;
- every paid entry into a beast form costs 20% of calculated maximum mana;
- Balance of Chimeras reduces positive transition costs by 30%.

The base mana cap 50+5*Spirit+2*(Level-1), recovery 600/2400
IN-GAME seconds and single-ceil paid-entry rounding are approved in v0.8.
Injury, unconsciousness, item cap buffs and post-level-up current mana stay open.
Legacy symbolic entry_cost remains for historical counterfactual tests.
"""

from fractions import Fraction

from rpg_resource_model import rounded_entry_cost

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

    Raw rational intermediate for diagnostics; billed mana is rounded up
    ONCE via canonical_paid_entry_cost() or paid_transition_cost().
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


def canonical_paid_entry_cost(max_mana: int | Fraction,
                              balance_of_chimeras: bool = False) -> Fraction:
    """Approved integer payment: ceil(M * 0.20 * (0.70 if perk else 1))."""
    return rounded_entry_cost(max_mana, balance_of_chimeras, "ceil")


def paid_transition_cost(source: str, target: str, max_mana: int | Fraction,
                         balance_of_chimeras: bool = False) -> Fraction:
    """Actual mana charged for a form transition under approved v0.8 rules."""
    if not source or not target:
        raise ValueError("Source and target form names cannot be blank")
    if source == target or target == HUMAN:
        return Fraction(0)
    return canonical_paid_entry_cost(max_mana, balance_of_chimeras)
