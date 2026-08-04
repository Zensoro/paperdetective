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


def test_triangle_verify_chart_stats_agree_no_crosstalk():
    # chart and stats agree with each other but both differ from claimed:
    # only the "chart" and "stats" legs should flag, NOT "chart-stats"
    r = triangle_verify(chart_value=80.0, claimed_value=50.0, stat_value=80.0)
    assert r["mismatch"] is True
    assert "chart-stats" not in r["mismatch_locations"]
    assert set(r["mismatch_locations"]) == {"chart", "stats"}


def test_triangle_verify_symmetric_verdict():
    # swapped args must give the same mismatch verdict (symmetry)
    a = triangle_verify(chart_value=10.0, claimed_value=5.0, stat_value=10.0)
    b = triangle_verify(chart_value=10.0, claimed_value=10.0, stat_value=5.0)
    assert a["mismatch"] == b["mismatch"]
