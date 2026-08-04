"""Evaluation: precision/recall/F1 against gold annotations."""
from __future__ import annotations


def evaluate(gold: dict[str, dict], predictions: dict[str, dict]) -> dict:
    tp = fp = fn = 0
    for pid, g in gold.items():
        expected = g.get("expected_findings", 0)
        got = len(predictions.get(pid, {}).get("detected_findings", []))
        tp += min(expected, got)
        fn += expected - min(expected, got)
        fp += max(0, got - expected)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(f1, 3), "tp": tp, "fp": fp, "fn": fn}
