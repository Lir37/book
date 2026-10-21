#!/usr/bin/env python3
"""Eidos v0.8 canonical base mana economy, plus labeled archival comparisons.

APPROVED: maximum = 50 + 5*Spirit + 2*(Level-1); human recovers a
full reserve in 600 IN-GAME seconds and beast in 2400 in-game seconds.
Beast upkeep costs zero. Paid form entry costs ceil(20% of maximum),
or ceil(14% with Balance of Chimeras): discount BEFORE a single ceil.
Internal regeneration accumulates as Fraction without per-second rounding.
UNKNOWN: equipment cap bonuses, statuses, death penalty, new skill costs.
"""
from __future__ import annotations

from fractions import Fraction

BEAST_REGEN_DIVISOR = 4  # AUTHOR APPROVED: not a scenario default
APPROVED_FULL_HUMAN_REFILL_SECONDS = 600  # IN-GAME seconds; author-approved


def _positive(value: int | Fraction, name: str) -> Fraction:
    result = Fraction(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def proposed_mana_cap(spirit: int, level: int = 1,
                      variant: str = "hybrid") -> Fraction:
    """'hybrid' is now CANON; flat/spirit_heavy are archival what-ifs.

    Starting at Spirit 15, level 1: canonical maximum is 125.
    Character stats at level 100 are unknown; do not extrapolate them.
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
                               APPROVED_FULL_HUMAN_REFILL_SECONDS) -> Fraction:
    """Canonical base rate at default 600 game seconds; override = what-if."""
    return _positive(max_mana, "maximum mana") / _positive(
        full_refill_seconds, "full refill seconds"
    )


def canonical_mana_cap(spirit: int, level: int) -> Fraction:
    """Approved base cap, excluding any future item/status cap modifiers."""
    return proposed_mana_cap(spirit, level, "hybrid")


def canonical_human_regen_rate(max_mana: int | Fraction) -> Fraction:
    """Approved natural human recovery, per IN-GAME second."""
    return candidate_human_regen_rate(max_mana)


def canonical_beast_regen_rate(max_mana: int | Fraction) -> Fraction:
    """Approved natural beast recovery, per IN-GAME second."""
    return canonical_human_regen_rate(max_mana) / BEAST_REGEN_DIVISOR


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
                       mode: str = "ceil") -> Fraction:
    """Canonical default = SINGLE CEIL after full discount, not two ceils.

    'exact' and 'half_up' remain archive-only counterfactual choices.
    Do not round fractional regeneration each second.
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
                                   mode: str = "ceil") -> int:
    """Count no-regeneration entries using canonical rounded prices."""
    price = rounded_entry_cost(max_mana, with_balance, mode)
    return int(_positive(max_mana, "maximum mana") // price)
