"""GRIM/SPRITE/Benford/p-curve data fabrication tests."""
import numpy as np
from paperdetective.detect.data_fabrication import (
    grim_test, sprite_test, benford_analysis, p_curve_analysis,
)


def test_grim_passes_near_zero_remainder():
    # mean=1.33 with n=2: 1.33*2=2.66=266*0.01 => possible, despite 2.66 % 0.01
    # rounding to ~8.7e-17 (near-zero) instead of exactly 0.0 in float arithmetic
    r = grim_test(mean=1.33, n=2, granularity=0.01)
    assert r["grim_passed"] is True


def test_grim_catches_impossible_mean():
    # mean=1.333 with n=2: 1.333*2=2.666, not an integer multiple of 0.01
    # (three decimals vs granularity's two) => impossible
    r = grim_test(mean=1.333, n=2, granularity=0.01)
    assert r["grim_passed"] is False


def test_grim_passes_possible_mean():
    # mean=1.335 with n=2, granularity 0.005: 1.335*2=2.67 ok at 0.005
    r = grim_test(mean=1.335, n=2, granularity=0.005)
    assert r["grim_passed"] is True


def test_sprite_catches_bad_sd():
    # sd > sd_max for n=4 => impossible standard deviation
    r = sprite_test(mean=10.0, sd=2.5, n=4)
    assert r["sprite_passed"] is False


def test_sprite_passes_plausible_sd():
    r = sprite_test(mean=10.0, sd=1.0, n=4)
    assert r["sprite_passed"] is True


def test_benford_flags_uniform_data():
    # uniform first digits 1-9 => digit 1 appears ~11% not 30.1%
    data = np.array([str(i) for i in range(9, 9000)])
    r = benford_analysis(data)
    assert r["digit1_pct"] < 0.20
    assert r["deviation"] > 0.05


def test_benford_passes_natural_data():
    # Fibonacci-ish natural numbers follow Benford
    fib = [1, 1]
    for _ in range(1000):
        fib.append(fib[-1] + fib[-2])
    r = benford_analysis(np.array([str(f) for f in fib if f > 0]))
    assert r["digit1_pct"] > 0.25


def test_p_curve_flags_p_hacking():
    # 30 p-values squeezed near 0.05 => suspicious p-hacking
    ps = [0.049, 0.049, 0.050, 0.048, 0.051] * 6
    r = p_curve_analysis(np.array(ps))
    assert r["p_hacking_suspicious"] is True


def test_p_curve_clean_distribution():
    ps = np.linspace(0.001, 0.049, 30)
    r = p_curve_analysis(ps)
    assert r["p_hacking_suspicious"] is False


def test_p_curve_short_sequence_includes_ratio():
    # short branch (<10 values) must still honor the dict contract
    r = p_curve_analysis([0.05, 0.04])
    assert "near_threshold_ratio" in r
    assert r["near_threshold_ratio"] == 0.0
