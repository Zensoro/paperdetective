"""Tests for multi-detector corroboration (convergent evidence)."""
import numpy as np
from PIL import Image

from paperdetective.analyze import _apply_corroboration, _extract_figure_ids
from paperdetective.schemas import EvidencePack, Finding


def _finding(method: str, confidence: float, figures: set[str] | None = None,
             figure_hits: dict | None = None) -> Finding:
    return Finding(
        id=f"FD-{method}",
        finding_type=["Image_Manipulation"],
        title=f"{method} finding",
        description="test",
        severity="Medium",
        evidence_pack=[EvidencePack(type="Visual", source_location="paper.pdf",
                                    quote="figA", basis="原文")],
        detection_method=method,
        confidence_score=confidence,
    )


def test_extract_figure_ids_drops_none():
    assert _extract_figure_ids("figA", None, "figB") == {"figA", "figB"}
    assert _extract_figure_ids(None, None) == set()


def test_single_detector_no_corroboration():
    fs = [_finding("ELA", 0.50)]
    hits = {"figA": [fs[0]]}
    _apply_corroboration(fs, hits)
    assert fs[0].confidence_score == 0.50
    assert fs[0].cross_references == []


def test_soft_signal_corroborated_by_hard_bumped_to_070():
    ela = _finding("ELA", 0.50)
    lane = _finding("LaneReuse", 0.90)
    fs = [ela, lane]
    hits = {"figA": fs}
    _apply_corroboration(fs, hits)
    assert ela.confidence_score == 0.70  # bumped by hard corroboration
    assert lane.confidence_score == 0.90  # hard evidence unchanged
    # cross references both ways
    ela_refs = {r["finding_id"] for r in ela.cross_references}
    lane_refs = {r["finding_id"] for r in lane.cross_references}
    assert "FD-LaneReuse" in ela_refs
    assert "FD-ELA" in lane_refs


def test_hard_hard_corroboration_no_bump_but_crossref():
    a = _finding("pHash", 0.90)
    b = _finding("RegionReuse", 0.90)
    fs = [a, b]
    hits = {"figA": fs}
    _apply_corroboration(fs, hits)
    assert a.confidence_score == 0.90
    assert b.confidence_score == 0.90
    assert len(a.cross_references) == 1
    assert len(b.cross_references) == 1


def test_corroboration_never_lowers_confidence():
    soft = _finding("BandELA", 0.55)
    hard = _finding("LaneReuse", 0.90)
    fs = [soft, hard]
    hits = {"figA": fs}
    _apply_corroboration(fs, hits)
    assert soft.confidence_score == 0.70
    assert hard.confidence_score == 0.90


def test_findings_on_different_figures_not_corroborated():
    a = _finding("ELA", 0.50)
    b = _finding("LaneReuse", 0.90)
    fs = [a, b]
    hits = {"figA": [a], "figB": [b]}
    _apply_corroboration(fs, hits)
    assert a.confidence_score == 0.50
    assert b.confidence_score == 0.90
    assert a.cross_references == []
    assert b.cross_references == []
