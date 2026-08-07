"""Tests for the lane-dataset dump tooling (no network / no real PDFs)."""
import numpy as np
import paperdetective.tools.dump_lane_dataset as d
from paperdetective.tools.dump_lane_dataset import (
    build_pairs, _lid, _dump_crop, _lane_content_ratio, discover_corpus,
)

PAPER = "10.1371_journal.pone.0071518"


def _rec(paper, fig, band, lane, cls, split="fraud"):
    return {
        "paper": paper, "figure": fig, "band": band, "lane": lane,
        "split": split, "class": cls, "best_corr": 0.98 if cls == "duplicate" else "",
    }


def test_lid_format_matches_manifest_ids():
    assert _lid(PAPER, "page6_Im5.png", 0, 4) == (
        "10.1371_journal.pone.0071518_page6_Im5.png_b0_l4"
    )


def test_dump_crop_normalizes_to_canvas():
    band = np.full((300, 40), 245, dtype=np.float32)
    band[50:250, 10:30] = 60  # a dark lane strip
    img = _dump_crop(band, 10, 30)
    assert img.size == d.DUMP_SIZE
    # the dark strip must survive (canvas is 255-padded, content < 200 somewhere)
    assert (np.asarray(img) < 200).any()


def test_lane_content_ratio_detects_ink():
    band = np.full((100, 50), 245, dtype=np.float32)
    assert _lane_content_ratio(band, 0, 50) == 0.0
    band[:, 0:25] = 50
    assert _lane_content_ratio(band, 0, 50) == 0.5


def test_build_pairs_uses_real_edges_not_self_pairs():
    hit_pairs = [
        (f"{PAPER}_figA_b0_l1", f"{PAPER}_figA_b0_l2", 0.97),
        (f"{PAPER}_figA_b0_l1", f"{PAPER}_figA_b0_l3", 0.96),
    ]
    records = [
        _rec(PAPER, "figA", 0, 1, "duplicate"),
        _rec(PAPER, "figA", 0, 2, "duplicate"),
        _rec(PAPER, "figA", 0, 3, "duplicate"),
        _rec(PAPER, "figA", 0, 9, "clean_lane"),
        _rec(PAPER, "figA", 0, 10, "clean_lane"),
        _rec("OTHER_PAPER", "figX", 0, 1, "clean_lane"),  # different paper
    ]
    pairs = build_pairs(records, hit_pairs, neg_per_pos=2)
    pos = [p for p in pairs if p["label"] == 1]
    neg = [p for p in pairs if p["label"] == 0]
    assert len(pos) == 2  # one row per hit edge
    assert all(p["lane_a"] != p["lane_b"] for p in pos)  # never self-pairs
    assert len(neg) == 4  # 2 positives x neg_per_pos=2
    # negatives must stay within the same paper as the positive (PAPER)
    assert all(p["lane_b"].startswith(PAPER) for p in neg)
    # the OTHER_PAPER clean lane must never appear
    assert all("OTHER_PAPER" not in p["lane_b"] for p in neg)


def test_build_pairs_skips_when_too_few_clean():
    hit_pairs = [(f"{PAPER}_figA_b0_l1", f"{PAPER}_figA_b0_l2", 0.97)]
    records = [
        _rec(PAPER, "figA", 0, 1, "duplicate"),
        _rec(PAPER, "figA", 0, 2, "duplicate"),
        # only one clean lane in this paper -> cannot form a within-paper negative
        _rec(PAPER, "figA", 0, 9, "clean_lane"),
    ]
    pairs = build_pairs(records, hit_pairs, neg_per_pos=3)
    assert len([p for p in pairs if p["label"] == 1]) == 1
    assert len([p for p in pairs if p["label"] == 0]) == 0


def _touch(p):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"%PDF-1.4\n")
    return p


def test_discover_corpus_top_level_is_fraud_and_clean_is_control(tmp_path):
    """Backwards compatibility: bare PDFs = fraud, clean/ = control."""
    _touch(tmp_path / "a.pdf")
    _touch(tmp_path / "clean" / "ctrl.pdf")

    got = {p.name: split for p, split in discover_corpus(tmp_path)}

    assert got == {"a.pdf": "fraud", "ctrl.pdf": "control"}


def test_discover_corpus_keeps_weak_labels_in_their_own_split(tmp_path):
    """A retracted/ subdir must NOT be promoted to the gold-standard fraud split.

    Papers retracted for image problems have no per-figure official finding, so
    mixing them into `fraud` would silently inflate the strength of the labels.
    """
    _touch(tmp_path / "gold.pdf")
    _touch(tmp_path / "retracted" / "weak1.pdf")
    _touch(tmp_path / "retracted" / "weak2.pdf")
    _touch(tmp_path / "clean" / "ctrl.pdf")

    got = {p.name: split for p, split in discover_corpus(tmp_path)}

    assert got["gold.pdf"] == "fraud"
    assert got["weak1.pdf"] == "retracted"
    assert got["weak2.pdf"] == "retracted"
    assert got["ctrl.pdf"] == "control"
    # exactly one paper carries the gold-standard label
    assert sum(1 for s in got.values() if s == "fraud") == 1


def test_discover_corpus_missing_dir_returns_empty(tmp_path):
    assert discover_corpus(tmp_path / "nope") == []
