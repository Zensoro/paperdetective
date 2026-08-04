"""Internal inconsistency detection via NLI-style triple verification."""
from paperdetective.detect.internal_inconsistency import (
    extract_numbers, compare_claims,
)


def test_extract_numbers():
    nums = extract_numbers("The mean is 12.3, sd 2.5, p=0.047, n=40")
    assert 12.3 in nums and 2.5 in nums and 0.047 in nums and 40 in nums


def test_compare_claims_contradiction():
    r = compare_claims("摘要: 含量为15%", "正文: 含量为25%", threshold=0.2)
    assert r["contradiction"] is True


def test_compare_claims_consistent():
    r = compare_claims("摘要: 含量为15%", "正文: 含量为15.2%", threshold=0.2)
    assert r["contradiction"] is False


def test_compare_claims_missing_numbers():
    r = compare_claims("没有数字的句子", "也是没有数字的", threshold=0.2)
    assert r["contradiction"] is None


def test_compare_claims_symmetric_verdict():
    r1 = compare_claims("10%", "8%", threshold=0.2)
    r2 = compare_claims("8%", "10%", threshold=0.2)
    assert r1["contradiction"] == r2["contradiction"]


def test_compare_claims_identical_strings_not_contradiction():
    r = compare_claims("0 vs 5", "0 vs 5", threshold=0.2)
    assert r["contradiction"] is False


def test_compare_claims_missing_numbers_has_full_shape():
    r = compare_claims("没有数字", "也没有数字", threshold=0.2)
    assert r["contradiction"] is None
    assert r["pairs"] == []
    assert r["threshold"] == 0.2
