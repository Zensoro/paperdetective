"""Triangle verification: chart value <-> claimed value <-> statistics."""
from __future__ import annotations


def reconstruct_chart_value(bar_height_px: float, pixel_min: float,
                            pixel_max: float, value_min: float,
                            value_max: float) -> float:
    if pixel_max == pixel_min:
        return 0.0
    ratio = (bar_height_px - pixel_min) / (pixel_max - pixel_min)
    return value_min + ratio * (value_max - value_min)


def triangle_verify(chart_value: float, claimed_value: float,
                    stat_value: float, threshold: float = 0.15) -> dict:
    """Any leg mismatching the others signals fabrication."""
    mismatches = []
    denom = claimed_value if claimed_value != 0 else 1.0
    if abs(chart_value - claimed_value) / abs(denom) > threshold:
        mismatches.append("chart")
    if abs(stat_value - claimed_value) / abs(denom) > threshold:
        mismatches.append("stats")
    if abs(chart_value - stat_value) / abs(denom) > threshold:
        mismatches.append("chart-stats")
    return {"mismatch": bool(mismatches), "mismatch_locations": mismatches,
            "values": {"chart": chart_value, "claimed": claimed_value,
                       "stats": stat_value},
            "violated": bool(mismatches)}
