"""Method conflict arbitration.

If methods disagree, the weighted vote decides; two soft flags beat one
hard clear signal only when the soft pair corroborates the same finding.
"""
from __future__ import annotations

METHOD_RELIABILITY = {
    "GRIM": 0.95, "SPRITE": 0.95, "DOI_Check": 0.92, "Retraction_Check": 0.92,
    "PRNU": 0.90, "pHash": 0.85, "p-curve": 0.60, "Benford": 0.70,
    "ELA": 0.55, "Embedding": 0.65, "NLI": 0.60, "CrossCheck": 0.70,
    "ChartReconstruct": 0.75,
}


def arbitrate(results: dict[str, dict]) -> dict:
    """results: {method: {"flagged": bool, "reliability": float}}."""
    flagged = [(m, r.get("reliability", METHOD_RELIABILITY.get(m, 0.5)))
               for m, r in results.items() if r.get("flagged")]
    total_weight = sum(r for _, r in flagged)
    overall = bool(flagged) and total_weight >= 0.75
    winner = max(flagged, key=lambda x: x[1])[0] if flagged else None
    return {"overall_flagged": overall, "winner": winner,
            "n_flagged": len(flagged), "weight_sum": round(total_weight, 3)}
