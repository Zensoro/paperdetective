"""Arbitration: resolve contradicting detection methods."""
from paperdetective.engine.arbitration import arbitrate, METHOD_RELIABILITY


def test_reliability_table():
    assert METHOD_RELIABILITY["GRIM"] > METHOD_RELIABILITY["p-curve"]


def test_arbitrate_hard_beats_soft():
    verdict = arbitrate({"GRIM": {"flagged": True, "reliability": 0.95},
                         "p-curve": {"flagged": False, "reliability": 0.6}})
    assert verdict["overall_flagged"] is True
    assert verdict["winner"] == "GRIM"


def test_arbitrate_soft_wins_with_corroboration():
    verdict = arbitrate({
        "GRIM": {"flagged": False, "reliability": 0.95},
        "p-curve": {"flagged": True, "reliability": 0.6},
        "Benford": {"flagged": True, "reliability": 0.7},
    })
    assert verdict["overall_flagged"] is True


def test_arbitrate_all_clean():
    verdict = arbitrate({"GRIM": {"flagged": False, "reliability": 0.95},
                         "Benford": {"flagged": False, "reliability": 0.7}})
    assert verdict["overall_flagged"] is False
