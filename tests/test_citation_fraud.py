"""Tests for the free citation-fraud detector (formerly pro)."""
from __future__ import annotations

from paperdetective.detect.citation_fraud import (
    check_doi_existence,
    find_dois,
    scan_retraction_keywords,
    validate_doi_format,
)
from paperdetective.ingest import Document
from paperdetective.analyze import run_detection


def test_validate_doi_format():
    assert validate_doi_format("10.1016/j.fake.2023.01.001")
    assert not validate_doi_format("not-a-doi")
    assert not validate_doi_format("10.123/fake with spaces")


def test_find_dois_deduplicates_and_trims():
    text = "See 10.1016/j.a.2023.001. and also 10.1016/j.a.2023.001;"
    dois = find_dois(text)
    assert dois == ["10.1016/j.a.2023.001"]


def test_check_doi_existence_none_on_network_failure():
    def fake_get(url, timeout=5):
        raise ConnectionError("offline")
    assert check_doi_existence("10.1016/j.x.2023.1", _get=fake_get) is None


def test_check_doi_existence_false_on_404():
    class Resp404:
        status = 404
    def fake_get(url, timeout=5):
        return Resp404()
    assert check_doi_existence("10.1016/j.x.2023.1", _get=fake_get) is False


def test_check_doi_existence_true_on_200():
    class Resp200:
        status = 200
    def fake_get(url, timeout=5):
        return Resp200()
    assert check_doi_existence("10.1016/j.x.2023.1", _get=fake_get) is True


def test_scan_retraction_keywords():
    assert scan_retraction_keywords({"title": "RETRACTION: a study", "type": ""}) == ["retract"]
    assert scan_retraction_keywords({"title": "normal", "type": ""}) == []


def test_doi_finding_emitted_in_core_pipeline():
    """A nonexistent DOI produces a Citation_Fabrication finding."""
    class Resp404:
        status = 404
    doc = Document(paper_id="p1", text="ref: 10.1016/j.fake.2023.01.001")
    result = run_detection([doc], _get=lambda url, timeout=5: Resp404())
    types = {ft for f in result.detected_findings for ft in f.finding_type}
    assert "Citation_Fabrication" in types
    assert "DOI_Check" in result.analysis_metadata["detectors_run"]


def test_doi_finding_skipped_when_verifiable():
    """A resolvable DOI should NOT produce a fabrication finding."""
    class Resp200:
        status = 200
    doc = Document(paper_id="p1", text="ref: 10.1016/j.real.2023.01.001")
    result = run_detection([doc], _get=lambda url, timeout=5: Resp200())
    types = {ft for f in result.detected_findings for ft in f.finding_type}
    assert "Citation_Fabrication" not in types
