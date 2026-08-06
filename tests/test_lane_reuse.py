"""Lane-level image forensics: duplicated-band detection for blots/gels."""
import numpy as np
from PIL import Image

from paperdetective.detect.lane_reuse import (
    segment_bands,
    segment_lanes,
    lane_profile,
    _lane_corr,
    _lane_block,
    _lane_entropy,
    detect_lane_reuse,
    cluster_lane_hits,
)


def _make_blot(rows=100, cols=400, seed=1, n_bands=2, n_lanes=8):
    """Synthetic western-blot: n_bands horizontal strips, each with n_lanes.

    Returns an RGB image. Lane content is random textured bands with a
    distinct vertical profile per lane index.
    """
    rng = np.random.default_rng(seed)
    h, w = rows * n_bands + 20 * (n_bands - 1), cols
    arr = np.full((h, w), 250, dtype=np.uint8)
    lane_w = cols // n_lanes
    for bi in range(n_bands):
        y0 = bi * (rows + 20)
        for li in range(n_lanes):
            x0 = li * lane_w
            # vertical profile: 8 segments with varying intensity, all filled
            profile = rng.uniform(0.3, 1.0, 8)
            seg_h = rows // 8
            for s, p in enumerate(profile):
                sy0 = y0 + s * seg_h
                sy1 = y0 + rows if s == 7 else sy0 + seg_h  # last seg fills to band end
                val = int(250 - 180 * p)
                arr[sy0:sy1, x0:x0 + lane_w - 6] = val
            # per-lane texture
            tex = rng.integers(-25, 25, (rows, lane_w - 6), dtype=np.int16)
            arr[y0:y0 + rows, x0:x0 + lane_w - 6] = np.clip(
                arr[y0:y0 + rows, x0:x0 + lane_w - 6].astype(np.int16) + tex, 0, 255
            ).astype(np.uint8)
    return Image.fromarray(arr).convert("RGB")


def _clone_lane(img, band_idx, lane_idx, target_band, target_lane):
    """Copy one lane's pixels into another lane (simulate band duplication).

    Bands are generated with equal height (rows), so a straight pixel copy
    is a valid simulation of a same-membrane splice.
    """
    rows, cols = 100, 400
    lane_w = cols // 8
    arr = np.array(np.asarray(img.convert("RGB")))
    src = arr[band_idx * (rows + 20):band_idx * (rows + 20) + rows,
              lane_idx * lane_w:(lane_idx + 1) * lane_w - 6]
    arr[target_band * (rows + 20):target_band * (rows + 20) + rows,
        target_lane * lane_w:(target_lane + 1) * lane_w - 6] = src
    return Image.fromarray(arr)


def test_segment_bands_finds_strips():
    img = _make_blot()
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    bands = segment_bands(gray)
    assert len(bands) == 2


def test_segment_lanes_finds_lanes():
    img = _make_blot()
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    bands = segment_bands(gray)
    lanes = segment_lanes(gray[bands[0][0]:bands[0][1], :])
    assert len(lanes) >= 6, f"expected >=6 lanes, got {len(lanes)}"


def test_lane_profile_distinct_for_different_content():
    img = _make_blot(seed=5)
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    bands = segment_bands(gray)
    b0 = gray[bands[0][0]:bands[0][1], :]
    lanes = segment_lanes(b0)
    # two clearly-different lanes should have a low correlation
    a = _lane_block(b0, *lanes[0])
    b = _lane_block(b0, *lanes[-1])
    assert _lane_corr(a, b) < 0.9


def test_detect_lane_reuse_finds_cloned_lane():
    img = _make_blot(seed=7)
    # clone lane 2 of band 0 into lane 5 of band 1
    forged = _clone_lane(img, 0, 2, 1, 5)
    hits = detect_lane_reuse({"figA": forged})
    assert any(
        h["band_a"] != h["band_b"] or h["lane_a"] != h["lane_b"]
        for h in hits
    ), f"expected a cross-band/cross-lane duplicate hit, got {hits}"


def test_detect_lane_reuse_no_hit_on_clean_blot():
    img = _make_blot(seed=11)
    hits = detect_lane_reuse({"figA": img})
    # clean synthetic blot: random per-lane profiles should NOT pass the
    # absolute + relative double threshold
    assert hits == [], f"expected no hits on clean blot, got {hits}"


def _mk_pair(fa, ba, la, fb, bb, lb, corr=0.99):
    return {
        "figure_a": fa, "band_a": ba, "lane_a": la,
        "box_a": (0, 0, 10, 100),
        "figure_b": fb, "band_b": bb, "lane_b": lb,
        "box_b": (0, 0, 10, 100),
        "correlation": corr, "pixel_diff": 3.0,
    }


def test_cluster_lane_hits_groups_star_network():
    # band0 lane7 copied to 4 destinations: one star, one cluster
    hits = [
        _mk_pair("p4", 0, 7, "p4", 1, 5),
        _mk_pair("p4", 0, 7, "p4", 2, 7),
        _mk_pair("p4", 0, 7, "p4", 3, 5),
        _mk_pair("p4", 0, 7, "p4", 4, 9),
    ]
    clusters = cluster_lane_hits(hits)
    assert len(clusters) == 1, f"expected 1 cluster, got {len(clusters)}"
    c = clusters[0]
    assert c["n_members"] == 5, c
    assert c["n_pairs"] == 4, c
    assert c["best_corr"] == 0.99
    assert c["figures"] == ["p4"]


def test_cluster_lane_hits_separates_disjoint_clusters():
    hits = [
        _mk_pair("p4", 0, 7, "p4", 1, 5),
        _mk_pair("p4", 0, 7, "p4", 2, 7),
        _mk_pair("p5", 1, 0, "p5", 3, 2),  # unrelated pair elsewhere
    ]
    clusters = cluster_lane_hits(hits)
    assert len(clusters) == 2, f"expected 2 clusters, got {len(clusters)}"
    sizes = sorted(c["n_members"] for c in clusters)
    assert sizes == [2, 3], sizes


def test_cluster_lane_hits_single_pair_keeps_one_cluster():
    hits = [_mk_pair("f1", 0, 1, "f1", 2, 3)]
    clusters = cluster_lane_hits(hits)
    assert len(clusters) == 1
    assert clusters[0]["n_members"] == 2
    assert clusters[0]["n_pairs"] == 1


def _make_tall_blot(rows=120, cols=400, seed=3, n_bands=2, n_lanes=8):
    """Like _make_blot but tall enough to pass the LANE_MIN_H gate."""
    return _make_blot(rows=rows, cols=cols, seed=seed,
                      n_bands=n_bands, n_lanes=n_lanes)


def test_lane_entropy_discriminates_texture_from_blank():
    img = _make_blot(seed=21)
    gray = np.asarray(img.convert("L"), dtype=np.float32)
    bands = segment_bands(gray)
    b0 = gray[bands[0][0]:bands[0][1], :]
    lanes = segment_lanes(b0)
    # textured lanes must have high entropy
    assert all(_lane_entropy(b0, *ln) >= 1.0 for ln in lanes[:3])
    # near-blank strips separated by thin dividers have low entropy
    blank = np.full((b0.shape[0], 400), 245, dtype=np.float32)
    for x in range(10, 400, 50):
        blank[:, x:x + 10] = 200  # 10px divider, wide enough to split
    blank_lanes = segment_lanes(blank)
    assert blank_lanes, "expected dividers to split strips"
    assert _lane_entropy(blank, *blank_lanes[0]) < 1.0


def test_height_gate_ignores_short_fragments():
    # two short strips (60px) with identical content must NOT be reported:
    # chart fragments, not blots
    rng = np.random.default_rng(5)
    h, w = 60, 400
    arr = np.full((h, w), 250, dtype=np.uint8)
    lane_w = w // 8
    for li in range(8):
        arr[:, li * lane_w:(li + 1) * lane_w - 6] = rng.integers(40, 220, (h, lane_w - 6))
    img = Image.fromarray(arr).convert("RGB")
    hits = detect_lane_reuse({"f1": img, "f2": img})
    assert hits == [], f"short identical strips must be gated out, got {hits}"


def test_entropy_gate_ignores_near_blank_strips():
    # two near-blank strips (identical, low entropy) must NOT be reported
    arr = np.full((150, 400), 250, dtype=np.uint8)
    lane_w = 50
    # faint outline boxes
    for x in (10, 60, 110, 160, 210, 260, 310, 360):
        arr[5:145, x:x + 3] = 200
    img = Image.fromarray(arr).convert("RGB")
    hits = detect_lane_reuse({"f1": img})
    assert hits == [], f"near-blank strips must be gated out, got {hits}"


def test_detect_lane_reuse_with_gates_still_finds_clone():
    # regression: the new gates must not kill the core clone detection.
    # rows must match _clone_lane's hardcoded 100px band height.
    img = _make_blot(rows=100, cols=400, seed=9)
    forged = _clone_lane(img, 0, 2, 1, 5)
    hits = detect_lane_reuse({"figA": forged})
    assert any(
        h["band_a"] != h["band_b"] or h["lane_a"] != h["lane_b"]
        for h in hits
    ), f"gates broke clone detection, got {hits}"
