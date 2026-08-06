"""Lane-level image forensics: duplicated-band detection for western blots / gels.

RegionReuse (grid-based panel hashing) cannot see a *band* copied into a
different lane at an arbitrary offset — fixed grids never cut the duplicated
band into the same tile. This module segments a figure into horizontal bands
(blot strips), then into vertical lanes, and reports lanes that are
*statistically implausibly* similar.

Design lessons from the fraud corpus (v0.6.0):

1. A *blot-like gate* is mandatory. Non-blot figures (cell images, montages,
   graphs) contain arbitrary content fragments that whitespace-projection
   misreads as "lanes"; running lane matching on them explodes false positives
   (measured: 513 hits on Yin 2012, 325 on Bo-Yu 2014). The gate requires
   each band to have a moderate lane count and every lane to be a NARROW
   vertical strip (width / band-height ratio <= 1.2).

2. A *pixel-level similarity* test is the right fingerprint — NOT a coarse
   intensity profile (normal repeats of the same protein across lanes make
   profiles look alike by construction, false-positives on clean blots) and
   NOT a perceptual hash (on narrow 10-20px lane strips phash saturates;
   clean and forged distance distributions overlap). Copy-paste fabrication
   reproduces pixel detail, so a lane pair scores high Pearson correlation
   AND low pixel-difference simultaneously. Two-stage confirm: correlation
   gate first (cheap), then pixel-diff confirm (decisive).

3. Real finding during control experiments: lanes the tool flags in
   "clean-looking" 2023 WB papers were verified as actual pixel-duplicated
   bands (59% identical pixels) — the tool catches fabrication that PubPeer
   has not yet.

4. Control-set gates (v0.6.0): on non-WB papers (meta-analyses, method
   papers) whitespace projection produces "lanes" out of forest-plot markers
   and flow-chart borders. Two cheap pre-filters restore precision without
   losing a single fraud case (8/8 fraud hit, 3/3 control papers clean):
   band height >= 100px (LANE_MIN_H) and per-lane gray entropy >= 1.0
   (LANE_MIN_ENTROPY). Measured without them: 1-5 false clusters per clean
   method paper.

First real-world motivation: Pfizer's official statement on the retracted
Nassirpour/Yin et al. papers confirmed "duplicated western blots" and
"duplicated bands inside western blots". On Nassirpour et al. 2013
(PLoS ONE 8:e62170, miR-221) Figure 6 blot shows lane triples with
correlation > 0.95. See docs/case-studies/corpus-2026-08.md.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

# Minimum band height (px) to treat as a blot strip.
BAND_MIN_H = 24
# Minimum white row-run (px) that separates two bands.
BAND_GAP_PX = 10
# Minimum lane width (px) to keep.
LANE_MIN_W = 8
# Minimum white column-run (px) that separates two lanes.
LANE_GAP_PX = 6
# Gray level below which a pixel counts as content.
CONTENT_BG = 205
# Number of vertical segments in a lane profile.
PROFILE_SEG = 8
# Blot-like gate: a band must have at least this many lanes...
MIN_LANES_PER_BAND = 5
# ...and at most this many (more => content mosaic, not a blot).
MAX_LANES_PER_BAND = 30
# Every lane in a real blot is a narrow strip: width <= this fraction of the
# band height. Wide blocks (graphs, photos, big panels) fail the gate.
MAX_LANE_WH_RATIO = 1.2
# A lane whose profile is nearly all-zero (empty/blank lane, or a bare
# marker lane) is skipped — blank lanes across bands are identical by
# construction and produce pure false positives.
PROFILE_MIN_ENERGY = 0.08
# Real blot membranes are tall (>= 100px): small chart fragments (forest-plot
# markers, legend ticks, flow-chart boxes) that whitespace projection splits
# into "lanes" are dropped by this height gate. Measured on the control set:
# without it, method papers yield 1-5 false clusters.
LANE_MIN_H = 100
# Blot bands have textured content: per-lane 32-bin gray histogram entropy
# >= 1.0. Near-blank strips (flow-chart borders, empty lanes, faint outlines)
# score ~0.3-0.9 and are dropped. Fraud lanes in the corpus: 0.9-4.3.
LANE_MIN_ENTROPY = 1.0
# Size lanes are resized to before comparison (x,y).
LANE_COMPARE_SIZE = (32, 8)
# Pearson-correlation gate for a "duplicate" lane pair.
CORR_THRESHOLD = 0.95
# Second-stage confirm: median absolute pixel difference must be below this
# (on the resized, brightness-normalized pair). Copy-paste pairs land ~2-6,
# merely-similar lanes ~20+.
PIXEL_DIFF_THRESH = 12


def _split_axis(density: np.ndarray, size: int, gap_px: int, min_len: int) -> list[tuple[int, int]]:
    """Split a 1-D content-density array into [start, end) intervals.

    A run of `density < 0.02` longer than `gap_px` terminates an interval.
    Intervals shorter than `min_len` are dropped.
    """
    intervals: list[tuple[int, int]] = []
    start: int | None = None
    gap_run = 0
    for i in range(size):
        if density[i] >= 0.02:
            if start is None:
                start = i
            gap_run = 0
        else:
            if start is not None:
                gap_run += 1
                if gap_run >= gap_px:
                    if i - gap_run + 1 - start >= min_len:
                        intervals.append((start, i - gap_run + 1))
                    start = None
                    gap_run = 0
    if start is not None and size - start >= min_len:
        intervals.append((start, size))
    return intervals


def segment_bands(gray: np.ndarray) -> list[tuple[int, int]]:
    """Horizontal bands (blot strips) via row whitespace projection."""
    h = gray.shape[0]
    density = (gray < CONTENT_BG).mean(axis=1)
    return _split_axis(density, h, BAND_GAP_PX, BAND_MIN_H)


def segment_lanes(band: np.ndarray) -> list[tuple[int, int]]:
    """Vertical lanes inside a band via column whitespace projection."""
    w = band.shape[1]
    density = (band < CONTENT_BG).mean(axis=0)
    return _split_axis(density, w, LANE_GAP_PX, LANE_MIN_W)


def lane_profile(band: np.ndarray, x0: int, x1: int, seg: int = PROFILE_SEG) -> np.ndarray:
    """Normalized per-segment mean intensity profile of one lane.

    Inverted so dark bands read high; normalized to [0, 1] so lanes of
    different absolute brightness (membrane background) are comparable.
    """
    h = band.shape[0]
    seg_h = max(1, h // seg)
    prof = np.empty(seg)
    for i in range(seg):
        y0, y1 = i * seg_h, min(h, (i + 1) * seg_h)
        strip = band[y0:y1, x0:x1]
        prof[i] = float(strip.mean()) if strip.size else 255.0
    prof = 255.0 - prof
    pmin, pmax = prof.min(), prof.max()
    if pmax - pmin > 1e-6:
        return (prof - pmin) / (pmax - pmin)
    return np.zeros_like(prof)


def profile_distance(a: np.ndarray, b: np.ndarray) -> float:
    """L1 distance between normalized profiles (0 = identical)."""
    return float(np.abs(a - b).mean())


def _is_blot_band(band: np.ndarray, lanes: list[tuple[int, int]]) -> bool:
    """Heuristic gate: does this horizontal strip look like a blot membrane?

    Real blot lanes are narrow vertical strips in moderate numbers. Content
    mosaics (montage figures) produce wide blocks or dozens of fragments and
    must be excluded — running lane matching on them causes false-positive
    explosions (measured on the fraud corpus).
    """
    if not (MIN_LANES_PER_BAND <= len(lanes) <= MAX_LANES_PER_BAND):
        return False
    bh = band.shape[0]
    for x0, x1 in lanes:
        if (x1 - x0) / bh > MAX_LANE_WH_RATIO:
            return False
    return True


def _lane_entropy(band: np.ndarray, x0: int, x1: int) -> float:
    """Shannon entropy of the lane's 32-bin gray histogram.

    Real blot lanes carry textured signal (entropy ~1-4); chart fragments and
    near-blank strips score < 1.0 and are excluded to keep false positives
    off the control set.
    """
    crop = np.asarray(band[:, x0:x1], dtype=np.uint8)
    hist, _ = np.histogram(crop, bins=32, range=(0, 256))
    hist = hist / max(hist.sum(), 1)
    return float(-np.sum(hist[hist > 0] * np.log2(hist[hist > 0])))


def _lane_block(band: np.ndarray, x0: int, x1: int):
    """Lane pixels resized to a fixed size for comparison."""
    tile = np.asarray(band[:, x0:x1], dtype=np.uint8)
    im = Image.fromarray(tile).resize(LANE_COMPARE_SIZE, Image.BILINEAR)
    return np.asarray(im, dtype=np.float32)


def _lane_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation between two lane pixel vectors."""
    a = a - a.mean()
    b = b - b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    if denom < 1e-9:
        return 0.0
    return float((a * b).sum() / denom)


def _lane_pixel_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Median absolute pixel difference (brightness-normalized pair)."""
    # normalize each to same mean/std so brightness difference doesn't dominate
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    return float(np.median(np.abs(a - b)))


def cluster_lane_hits(hits: list[dict]) -> list[dict]:
    """Fold pairwise duplicate hits into connected lane-clusters.

    A forged lane is usually copied to several destinations, producing a
    star of pairwise hits (e.g. band0 lane7 <-> band1 lane5, band2 lane7,
    band3 lane5, band4 lane9...). Reporting every pair drowns the report in
    noise — measured 62 hits on a single figure of the fraud corpus. This
    Union-Find pass groups mutually-linked lanes into one finding per
    cluster so a duplicated-band network reads as a single alarm.

    Each returned cluster:
      members    - lane descriptors ({figure, band, lane, box})
      n_members  - lanes in the cluster
      n_pairs    - pairwise hits that connect them
      best_corr  - strongest correlation inside the cluster
      best_pair  - the strongest hit dict (for the report quote)
      figures    - sorted figure ids involved
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def key(h: dict, side: str) -> str:
        return f"{h['figure_' + side]}:{h['band_' + side]}:{h['lane_' + side]}"

    for h in hits:
        union(key(h, "a"), key(h, "b"))

    members: dict[str, dict] = {}
    edge_lists: dict[str, list] = {}
    for h in hits:
        root = find(key(h, "a"))
        nodes = members.setdefault(root, {})
        for side in ("a", "b"):
            k = key(h, side)
            nodes[k] = {
                "figure": h[f"figure_{side}"],
                "band": h[f"band_{side}"],
                "lane": h[f"lane_{side}"],
                "box": h[f"box_{side}"],
            }
        edge_lists.setdefault(root, []).append(h)

    clusters = []
    for root, nodes in members.items():
        edges = edge_lists[root]
        best = max(edges, key=lambda e: e["correlation"])
        clusters.append({
            "members": [nodes[k] for k in sorted(nodes)],
            "n_members": len(nodes),
            "n_pairs": len(edges),
            "best_corr": best["correlation"],
            "best_pair": best,
            "figures": sorted({n["figure"] for n in nodes.values()}),
        })
    # loudest first: more evidence pairs, then stronger correlation
    clusters.sort(key=lambda c: (-c["n_pairs"], -c["best_corr"]))
    return clusters


def detect_lane_reuse(images: dict[str, Image.Image]) -> list[dict]:
    """Detect pixel-level lane duplication across bands/figures.

    Pipeline:
      1. segment bands, gate each band as blot-like, drop blank lanes;
      2. compare every lane pair: Pearson correlation gate, then pixel-diff
         confirm;
      3. report pairs passing BOTH criteria.

    Returns a list of dicts: figure/band/lane ids + pixel boxes + corr/diff.
    """
    lanes_all: list[dict] = []
    for fig_id, img in images.items():
        gray = np.asarray(img.convert("L"), dtype=np.float32)
        for bi, (y0, y1) in enumerate(segment_bands(gray)):
            if y1 - y0 < LANE_MIN_H:
                continue  # chart fragments / tiny strips are not blots
            band = gray[y0:y1, :]
            lanes = segment_lanes(band)
            if not _is_blot_band(band, lanes):
                continue
            for li, (x0, x1) in enumerate(lanes):
                prof = lane_profile(band, x0, x1)
                if float(prof.mean()) < PROFILE_MIN_ENERGY:
                    continue  # blank / bare-marker lane
                if _lane_entropy(band, x0, x1) < LANE_MIN_ENTROPY:
                    continue  # near-blank strip / chart artifact
                lanes_all.append({
                    "figure": fig_id, "band": bi, "lane": li,
                    "y0": y0, "y1": y1, "x0": x0, "x1": x1,
                    "block": _lane_block(band, x0, x1),
                })

    hits: list[dict] = []
    for i in range(len(lanes_all)):
        for j in range(i + 1, len(lanes_all)):
            a, b = lanes_all[i], lanes_all[j]
            if a["figure"] == b["figure"] and a["band"] == b["band"] and a["lane"] == b["lane"]:
                continue
            corr = _lane_corr(a["block"], b["block"])
            if corr < CORR_THRESHOLD:
                continue
            diff = _lane_pixel_diff(a["block"], b["block"])
            if diff > PIXEL_DIFF_THRESH:
                continue
            hits.append({
                "figure_a": a["figure"], "band_a": a["band"], "lane_a": a["lane"],
                "box_a": (a["x0"], a["y0"], a["x1"], a["y1"]),
                "figure_b": b["figure"], "band_b": b["band"], "lane_b": b["lane"],
                "box_b": (b["x0"], b["y0"], b["x1"], b["y1"]),
                "correlation": round(corr, 4),
                "pixel_diff": round(diff, 2),
            })
    return hits
