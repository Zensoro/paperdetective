"""Citation fraud detection: DOI format + existence (mockable) + retraction flags."""
from urllib.error import HTTPError

from paperdetective.detect.citation_fraud import (
    DEFAULT_TIMEOUT, validate_doi_format, check_doi_existence, scan_retraction_keywords,
)


def test_doi_format_valid():
    assert validate_doi_format("10.1016/j.cell.2023.04.021") is True


def test_doi_format_invalid():
    assert validate_doi_format("not-a-doi") is False
    assert validate_doi_format("") is False


def test_doi_format_whitespace_padded():
    assert validate_doi_format(" 10.1016/j.cell.2023.04.021 ") is True


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


def test_doi_existence_network_down():
    def fake_get(url, timeout):
        raise OSError("no route to host")
    assert check_doi_existence("10.1016/j.cell.2023.04.021", _get=fake_get) is None


def test_doi_existence_http_404_error():
    def fake_get(url, timeout):
        raise HTTPError(url, 404, "Not Found", {}, None)
    assert check_doi_existence("10.1016/j.fake.0000", _get=fake_get) is False


def test_doi_existence_uses_default_timeout():
    seen = {}
    def fake_get(url, timeout):
        seen["timeout"] = timeout
        class R: status_code = 200
        return R()
    check_doi_existence("10.1016/j.cell.2023.04.021", _get=fake_get)
    assert seen["timeout"] == DEFAULT_TIMEOUT == 5.0


def test_retraction_keywords():
    meta = {"title": "RETRACTED: A study of X", "type": "Retraction"}
    flags = scan_retraction_keywords(meta)
    assert "retract" in flags
    assert "correction" not in flags


def test_retraction_no_flags_clean():
    meta = {"title": "A normal study", "type": "ResearchArticle"}
    assert scan_retraction_keywords(meta) == []


def test_retraction_corrigendum_flag():
    meta = {"title": "Corrigendum to: A study of X", "type": "Corrigendum"}
    assert "corrigendum" in scan_retraction_keywords(meta)
