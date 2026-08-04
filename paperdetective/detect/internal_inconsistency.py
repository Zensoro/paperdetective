"""Internal inconsistency: cross-section numeric claim comparison.

Numeric extraction + relative deviation. The full NLI pass (premise->conclusion
consistency) is an LLM call; we ship the numeric core now and leave the LLM
hook as a pluggable function (see `nli_verdict`).
"""
from __future__ import annotations

import re
from typing import Callable, Optional

NUM_RE = re.compile(r"-?\d+\.?\d*")


def extract_numbers(text: str) -> list[float]:
    return [float(m) for m in NUM_RE.findall(text)]


def compare_claims(claim_a: str, claim_b: str, threshold: float = 0.2) -> dict:
    """Compare numeric content of two text claims (e.g. abstract vs body)."""
    a = extract_numbers(claim_a)
    b = extract_numbers(claim_b)
    if not a or not b:
        return {"contradiction": None, "reason": "missing numbers", "pairs": [], "threshold": threshold}
    # align by order; compare each common position (a[i] vs b[i])
    contradictions = []
    for x, y in zip(a, b):
        denom = max(abs(x), abs(y), 1e-9)
        if abs(x - y) / denom > threshold and abs(x - y) > 1e-6:
            contradictions.append((x, y))
    return {
        "contradiction": bool(contradictions),
        "pairs": contradictions[:5],
        "threshold": threshold,
    }


def nli_verdict(premise: str, conclusion: str, llm: Optional[Callable] = None) -> Optional[str]:
    """Optional LLM pass: returns 'contradiction'/'entailment'/'neutral' or None offline."""
    if llm is None:
        return None
    return llm(premise, conclusion)
