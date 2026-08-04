"""Citation fraud detection: DOI format + existence (mockable) + retraction flags."""
from paperdetective.detect.citation_fraud import (
    validate_doi_format, check_doi_existence, scan_retraction_keywords,
)


def test_doi_format_valid():
    assert validate_doi_format("10.1016/j.cell.2023.04.021") is True


def test_doi_format_invalid():
    assert validate_doi_format("not-a-doi") is False
    assert validate_doi_format("") is False


def test_doi_existence_mock_200():
    # fake transport layer: respond 200 -> DOI exists
    def fake_get(url, timeout):
        class R: status_code = 200
        return R()
    assert check_doi_existence("10.1016/j.cell.2023.04.021", _get=fake_get) is True


def test_doi_existence_mock_404():
    def fake_get(url, timeout):
        class R: status_code = 404
        return R()
    assert check_doi_existence("10.1016/j.fake.0000", _get=fake_get) is False


def test_retraction_keywords():
    meta = {"title": "RETRACTED: A study of X", "type": "Retraction"}
    flags = scan_retraction_keywords(meta)
    assert "retract" in flags
    assert "correction" not in flags


def test_retraction_no_flags_clean():
    meta = {"title": "A normal study", "type": "ResearchArticle"}
    assert scan_retraction_keywords(meta) == []
