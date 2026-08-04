"""Data fabrication detection: GRIM, SPRITE, Benford extension, p-curve.

All functions are pure; they take extracted numbers and return verdict dicts.
"""
from __future__ import annotations

import numpy as np

BENFORD_EXPECTED = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
                    6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}


def grim_test(mean: float, n: int, granularity: float = 0.01) -> dict:
    """GRIM: mean * n must be a multiple of granularity.

    Due to floating-point representation the remainder of the division
    may round to 0 or to the granularity itself, so both are accepted.
    """
    total = mean * n
    rem = total % granularity
    return {
        "grim_passed": bool(rem == 0.0 or abs(rem - granularity) < 1e-9),
        "mean": mean, "n": n, "granularity": granularity,
        "total": round(total, 4),
    }


def sprite_test(mean: float, sd: float, n: int) -> dict:
    """SPRITE: sd cannot exceed the max possible given mean and n."""
    sd_max = 0.5 * np.sqrt(n / (n - 1)) if n > 1 else 0.0
    return {
        "sprite_passed": bool(sd <= sd_max * 2.0),  # heuristic cap, conservative
        "sd": sd, "sd_max_possible": round(sd_max, 4), "n": n,
    }


def _leading_digit(s: str) -> int:
    s = s.strip().lstrip("-+.")
    for ch in s:
        if ch.isdigit() and ch != "0":
            return int(ch)
    return 0


def benford_analysis(numbers) -> dict:
    """Check leading-digit distribution against Benford's law."""
    digits = np.array([_leading_digit(str(x)) for x in numbers])
    digits = digits[digits != 0]
    if len(digits) == 0:
        return {"digit1_pct": 0.0, "deviation": 1.0, "n": 0}
    counts = np.bincount(digits, minlength=10) / len(digits)
    deviation = max(abs(counts[d] - BENFORD_EXPECTED[d]) for d in range(1, 10))
    return {
        "digit1_pct": round(float(counts[1]), 4),
        "deviation": round(float(deviation), 4),
        "n": int(len(digits)),
    }


def p_curve_analysis(p_values) -> dict:
    """p-curve: proportion of p-values in 0.04-0.05 bin vs rest."""
    ps = np.asarray(p_values, dtype=float)
    ps = ps[(ps > 0) & (ps < 1)]
    if len(ps) < 10:
        return {"p_hacking_suspicious": False, "n": int(len(ps))}
    near_threshold = np.sum((ps >= 0.04) & (ps <= 0.05))
    ratio = near_threshold / len(ps)
    # >30% of p-values crammed within 1% of threshold = suspicious
    return {
        "p_hacking_suspicious": bool(ratio > 0.30),
        "near_threshold_ratio": round(float(ratio), 4),
        "n": int(len(ps)),
    }
