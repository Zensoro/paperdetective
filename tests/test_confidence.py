"""Layered confidence engine tests."""
from paperdetective.engine.confidence import (
    confidence_score, HARD_EVIDENCE, SOFT_SIGNAL,
)

HARD = {"GRIM", "SPRITE", "PRNU", "DOI_Check", "Retraction_Check"}


def test_hard_evidence_high_confidence():
    assert HARD.issubset(HARD_EVIDENCE)
    assert confidence_score(evidence=["GRIM"], soft=0, n_corroborating=0) >= 0.85


def test_sprite_is_hard_evidence():
    assert confidence_score(evidence=["SPRITE"], soft=0, n_corroborating=0) >= 0.85


def test_soft_derived_from_evidence():
    s = confidence_score(evidence=["p-curve"], n_corroborating=0)
    assert 0.40 <= s <= 0.59


def test_soft_signal_bounded():
    s = confidence_score(evidence=["p-curve"], soft=1, n_corroborating=0)
    assert 0.40 <= s <= 0.59


def test_soft_signals_stack_to_hard():
    s = confidence_score(evidence=[], soft=3, n_corroborating=0)
    assert s >= 0.85  # 3 soft signals escalate to hard


def test_soft_signal_plus_corroboration():
    s = confidence_score(evidence=["p-curve"], soft=1, n_corroborating=2)
    assert 0.60 <= s <= 0.84


def test_no_evidence_is_low():
    assert confidence_score(evidence=[], soft=0, n_corroborating=0) <= 0.39


def test_internal_knowledge_cap():
    s = confidence_score(evidence=["GRIM"], soft=0, n_corroborating=0,
                         internal_knowledge=True)
    assert s <= 0.60
