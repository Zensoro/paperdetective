"""GRIM/SPRITE/Benford/p-curve data fabrication tests."""
import numpy as np
from paperdetective.detect.data_fabrication import (
    grim_test, sprite_test, benford_analysis, p_curve_analysis,
)


def test_grim_passes_consistent_mean():
    # mean=1.33 with n=3: 总分 4 -> 4/3=1.3333 四舍五入到两位即 1.33 => 合法
    r = grim_test(mean=1.33, n=3, granularity=0.01)
    assert r["grim_passed"] is True
    assert r["violated"] is False


def test_grim_catches_impossible_mean():
    # mean=2.66 with n=2: 可能的总分只有整数 5 或 6 -> 2.5 或 3.0，
    # 无论怎么舍入都得不到 2.66 => 不可能
    r = grim_test(mean=2.66, n=2, granularity=0.01)
    assert r["grim_passed"] is False
    assert r["violated"] is True


def test_grim_catches_three_decimal_mean_with_small_n():
    # mean=1.333 with n=2: 3/2=1.5，与 1.333 的差距远超舍入窗口 => 不可能
    r = grim_test(mean=1.333, n=2, granularity=0.01)
    assert r["grim_passed"] is False
    assert r["violated"] is True


def test_grim_passes_possible_mean():
    # mean=1.335 with n=200, granularity 0.005: 267/200=1.335 精确成立
    r = grim_test(mean=1.335, n=200, granularity=0.005)
    assert r["grim_passed"] is True
    assert r["violated"] is False


def test_grim_rejects_invalid_n():
    import pytest
    with pytest.raises(ValueError):
        grim_test(mean=1.0, n=0)


def test_sprite_catches_bad_sd():
    # sd > sd_max for n=4 => impossible standard deviation
    r = sprite_test(mean=10.0, sd=2.5, n=4)
    assert r["sprite_passed"] is False
    assert r["violated"] is True


def test_sprite_passes_plausible_sd():
    r = sprite_test(mean=10.0, sd=1.0, n=4)
    assert r["sprite_passed"] is True
    assert r["violated"] is False


def test_sprite_reports_strict_bound_and_used_cap():
    # n=4 => sd_max_possible=0.5774 (strict, rounded), sd_cap=1.1547 (2x used)
    r = sprite_test(mean=10.0, sd=1.0, n=4)
    assert r["sd_max_possible"] == 0.5774
    assert r["sd_cap"] == 1.1547


def test_benford_flags_uniform_data():
    # uniform first digits 1-9 => digit 1 appears ~11% not 30.1%
    data = np.array([str(i) for i in range(9, 9000)])
    r = benford_analysis(data)
    assert r["digit1_pct"] < 0.20
    assert r["deviation"] > 0.10
    assert r["violated"] is True


def test_benford_passes_natural_data():
    # Fibonacci-ish natural numbers follow Benford
    fib = [1, 1]
    for _ in range(1000):
        fib.append(fib[-1] + fib[-2])
    r = benford_analysis(np.array([str(f) for f in fib if f > 0]))
    assert r["digit1_pct"] > 0.25
    assert r["deviation"] < 0.10
    assert r["violated"] is False


def test_benford_empty_input_is_not_a_fraud_signal():
    # 没有可用数字 = 不适用，绝不能误报为造假
    r = benford_analysis([])
    assert r["n"] == 0
    assert r["violated"] is False


def test_p_curve_flags_p_hacking():
    # 30 p-values squeezed near 0.05 => suspicious p-hacking
    ps = [0.049, 0.049, 0.050, 0.048, 0.051] * 6
    r = p_curve_analysis(np.array(ps))
    assert r["p_hacking_suspicious"] is True
    assert r["violated"] is True


def test_p_curve_clean_distribution():
    ps = np.linspace(0.001, 0.049, 30)
    r = p_curve_analysis(ps)
    assert r["p_hacking_suspicious"] is False
    assert r["violated"] is False


def test_p_curve_short_sequence_includes_ratio():
    # short branch (<10 values) must still honor the dict contract
    r = p_curve_analysis([0.05, 0.04])
    assert "near_threshold_ratio" in r
    assert r["near_threshold_ratio"] == 0.0
    assert r["violated"] is False
