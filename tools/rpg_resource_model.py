#!/usr/bin/env python3
"""Canonical regen RATIO and author-unapproved numeric economy experiments.

CANON (2026-10-21): beast mana recovery is FOUR TIMES SLOWER than human.
Entering an unlocked beast form costs 20% of calculated max mana or 14% after
Balance of Chimeras. Form upkeep and voluntary return to human cost zero.

NOT CANON: absolute mana cap from Spirit/level, absolute recovery speed,
rounding to integer or fractional displayed mana, regeneration interruptions.
All proposed functions are explicitly experimental.
"""
from __future__ import annotations

from fractions import Fraction

BEAST_REGEN_DIVISOR = 4  # AUTHOR APPROVED: not a scenario default
EXPERIMENTAL_FULL_HUMAN_REFILL_SECONDS = 600  # PROJECT: 10 min, not canon


def _positive(value: int | Fraction, name: str) -> Fraction:
    result = Fraction(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def proposed_mana_cap(spirit: int, level: int = 1,
                      variant: str = "hybrid") -> Fraction:
    """Compare candidate mana-cap formulas. No one variant is canonical.

    flat = 50 + 5*Spirit, matching the earlier research's 125 at Spirit=15.
    hybrid = 50 + 5*Spirit + 2*(level-1), starting at the same 125.
    spirit_heavy = 40 + 6*Spirit + (level-1), starting at 130.
    Growth in available stats at level 100 remains unknown and is NOT modeled.
    """
    if not isinstance(spirit, int) or not isinstance(level, int):
        raise TypeError("Spirit and level must be integer")
    if spirit < 1 or not 1 <= level <= 100:
        raise ValueError("Spirit must be positive, level between 1 and 100")
    if variant == "flat":
        return Fraction(50 + 5 * spirit)
    if variant == "hybrid":
        return Fraction(50 + 5 * spirit + 2 * (level - 1))
    if variant == "spirit_heavy":
        return Fraction(40 + 6 * spirit + (level - 1))
    raise ValueError(f"Unknown experimental cap variant: {variant}")


def candidate_human_regen_rate(max_mana: int | Fraction,
                               full_refill_seconds: int | Fraction =
                               EXPERIMENTAL_FULL_HUMAN_REFILL_SECONDS) -> Fraction:
    """Experimental constant rate; true base recovery is not approved."""
    return _positive(max_mana, "maximum mana") / _positive(
        full_refill_seconds, "full refill seconds"
    )


def effective_regen_rate(human_rate: int | Fraction, form: str) -> Fraction:
    """Enforce APPROVED one-quarter beast regeneration ratio exactly."""
    rate = _positive(human_rate, "human recovery rate")
    if form == "human":
        return rate
    if not form:
        raise ValueError("Form name is required")
    return rate / BEAST_REGEN_DIVISOR


def regenerated_mana(max_mana: int | Fraction, current: int | Fraction,
                     seconds: int | Fraction, human_rate: int | Fraction,
                     form: str) -> Fraction:
    """Apply explicit rate for a continuous period, capped at max mana."""
    cap, mana, duration = Fraction(max_mana), Fraction(current), Fraction(seconds)
    _positive(cap, "maximum mana")
    if not 0 <= mana <= cap:
        raise ValueError("Mana must be between zero and maximum")
    if duration < 0:
        raise ValueError("Duration cannot be negative")
    if duration == 0:
        return mana
    return min(cap, mana + effective_regen_rate(human_rate, form) * duration)


def rounded_entry_cost(max_mana: int | Fraction, with_balance: bool,
                       mode: str = "exact") -> Fraction:
    """Project comparison; apply the discount BEFORE rounding, only once.

    'exact': internal fractional mana; 'ceil': smallest integer >= cost;
    'half_up': nearest integer, ties away from zero.
    None of these display/rounding conventions has been approved.
    """
    cap = _positive(max_mana, "maximum mana")
    raw = cap * (Fraction(7, 50) if with_balance else Fraction(1, 5))
    if mode == "exact":
        return raw
    if mode == "ceil":
        return Fraction((raw.numerator + raw.denominator - 1) // raw.denominator)
    if mode == "half_up":
        return Fraction((2 * raw.numerator + raw.denominator) // (2 * raw.denominator))
    raise ValueError("Unknown rounding candidate")


def unassisted_entries_at_full_cap(max_mana: int | Fraction,
                                   with_balance: bool,
                                   mode: str = "exact") -> int:
    """Count zero-regeneration entries (each exit to human is free)."""
    price = rounded_entry_cost(max_mana, with_balance, mode)
    return int(_positive(max_mana, "maximum mana") // price)
