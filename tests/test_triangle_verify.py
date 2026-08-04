"""Triangle chain: chart-reconstructed value vs claimed value vs stats."""
from paperdetective.engine.triangle_verify import (
    reconstruct_chart_value, triangle_verify,
)


def test_reconstruct_chart_value_bar():
    # bar pixel height 50, axis: 0px->0, 100px->100
    v = reconstruct_chart_value(bar_height_px=50, pixel_min=0, pixel_max=100,
                                value_min=0, value_max=100)
    assert abs(v - 50.0) < 1e-6


def test_triangle_verify_all_consistent():
    r = triangle_verify(chart_value=50.0, claimed_value=50.5, stat_value=50.0)
    assert r["mismatch"] is False


def test_triangle_verify_chart_claims_disagree():
    r = triangle_verify(chart_value=80.0, claimed_value=50.0, stat_value=50.0)
    assert r["mismatch"] is True
    assert "chart" in r["mismatch_locations"]


def test_triangle_verify_stats_disagree():
    r = triangle_verify(chart_value=50.0, claimed_value=50.0, stat_value=70.0)
    assert r["mismatch"] is True
    assert "stats" in r["mismatch_locations"]
