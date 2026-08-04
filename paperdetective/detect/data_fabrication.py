"""Data fabrication detection: GRIM, SPRITE, Benford extension, p-curve.

All functions are pure; they take extracted numbers and return verdict dicts.
"""
from __future__ import annotations

import numpy as np

BENFORD_EXPECTED = {1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
                    6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046}


def grim_test(mean: float, n: int, granularity: float = 0.01) -> dict:
    """GRIM test (Brown & Heathers 2017).

    For integer-valued data (e.g. Likert scales, counts), a reported mean
    rounded to a given ``granularity`` is *consistent* iff there exists an
    integer total T such that T / n, rounded to the same granularity,
    reproduces the reported mean. Equivalently: the nearest integer to
    ``mean * n``, divided by ``n``, must round back to ``mean``.
    """
    if n < 1:
        raise ValueError("n must be a positive integer")
    total = mean * n
    nearest_total = round(total)
    # half-width of the rounding window implied by the reporting granularity
    tolerance = granularity / 2.0 + 1e-12
    reconstructed = nearest_total / n
    passed = bool(abs(reconstructed - mean) <= tolerance)
    return {
        "grim_passed": passed,
        "violated": not passed,
        "mean": mean, "n": n, "granularity": granularity,
        "total": round(total, 4),
        "nearest_integer_total": int(nearest_total),
        "reconstructed_mean": round(reconstructed, 6),
    }


def sprite_test(mean: float, sd: float, n: int) -> dict:
    """SPRITE heuristic: sd should not exceed a plausible cap for n
    observations of bounded [0,1] data. Uses a conservative 2x tolerance."""
    sd_max = 0.5 * np.sqrt(n / (n - 1)) if n > 1 else 0.0
    sd_cap = sd_max * 2.0
    passed = bool(sd <= sd_cap)
    return {
        "sprite_passed": passed,
        "violated": not passed,
        "sd": sd,
        "sd_max_possible": round(sd_max, 4),
        "sd_cap": round(sd_cap, 4),
        "n": n,
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
        # no usable numbers: not applicable, must NOT be flagged as fraud
        return {"digit1_pct": 0.0, "deviation": 0.0, "n": 0, "violated": False}
    counts = np.bincount(digits, minlength=10) / len(digits)
    deviation = max(abs(counts[d] - BENFORD_EXPECTED[d]) for d in range(1, 10))
    return {
        "digit1_pct": round(float(counts[1]), 4),
        "deviation": round(float(deviation), 4),
        "n": int(len(digits)),
        # deviation > 0.10 = significant Benford violation
        "violated": bool(deviation > 0.10),
    }


def p_curve_analysis(p_values) -> dict:
    """p-curve: proportion of p-values in 0.04-0.05 bin vs rest."""
    ps = np.asarray(p_values, dtype=float)
    ps = ps[(ps > 0) & (ps < 1)]
    if len(ps) < 10:
        return {
            "p_hacking_suspicious": False,
            "violated": False,
            "near_threshold_ratio": 0.0,
            "n": int(len(ps)),
        }
    near_threshold = np.sum((ps >= 0.04) & (ps <= 0.05))
    ratio = near_threshold / len(ps)
    # >30% of p-values crammed within 1% of threshold = suspicious
    suspicious = bool(ratio > 0.30)
    return {
        "p_hacking_suspicious": suspicious,
        "violated": suspicious,
        "near_threshold_ratio": round(float(ratio), 4),
        "n": int(len(ps)),
    }
