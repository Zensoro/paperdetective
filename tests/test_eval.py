"""Eval: score findings against gold annotations."""
import pytest

from paperdetective.eval import evaluate


def test_evaluate_perfect():
    gold = {"p1": {"expected_findings": 2}}
    pred = {"p1": {"detected_findings": [1, 2]}}
    r = evaluate(gold, pred)
    assert r["precision"] == 1.0 and r["recall"] == 1.0


def test_evaluate_partial():
    gold = {"p1": {"expected_findings": 3}}
    pred = {"p1": {"detected_findings": [1]}}
    r = evaluate(gold, pred)
    assert r["recall"] == pytest.approx(1.0 / 3.0, abs=1e-3)
