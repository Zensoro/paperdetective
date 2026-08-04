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
