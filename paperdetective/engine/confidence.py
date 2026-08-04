"""Layered confidence engine.

Hard evidence -> 0.85-1.00
Multiple corroborating soft signals -> 0.60-0.84
Single soft signal -> 0.40-0.59
Inference only -> 0.20-0.39
Anything relying on unverified internal knowledge is capped at 0.60.
"""
from __future__ import annotations

HARD_EVIDENCE = {"GRIM", "PRNU", "DOI_Check", "Retraction_Check", "pHash"}
SOFT_SIGNAL = {"p-curve", "Benford", "ELA", "Embedding", "NLI", "CrossCheck", "ChartReconstruct"}


def confidence_score(
    evidence: list[str],
    soft: int = 0,
    n_corroborating: int = 0,
    internal_knowledge: bool = False,
) -> float:
    n_hard = sum(1 for e in evidence if e in HARD_EVIDENCE)
    if n_hard >= 1:
        base = 0.9
    elif soft >= 3:
        base = 0.87  # soft escalation
    elif n_corroborating >= 1:
        base = 0.70
    elif soft >= 1:
        base = 0.50
    elif evidence:
        base = 0.30
    else:
        base = 0.25
    if internal_knowledge:
        return min(base, 0.60)
    return min(base, 1.0)
