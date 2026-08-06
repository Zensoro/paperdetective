"""Region-level image forensics: panel-split perceptual hashing.

Whole-figure pHash cannot see sub-figure reuse (e.g. a western-blot panel that
was duplicated or moved between two figures). This module splits each figure
into panels via whitespace projection, hashes every panel, and reports
near-duplicate panels across *different* source locations.

First real-world motivation: the ORI-confirmed fabrication in Brand et al. 2013
(PLoS ONE 8:e71518) re-used western-blot panels within Figures 1/6/7 — invisible
to whole-figure pHash, but detectable at panel level. See
docs/case-studies/her3-brand-2013.md.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .image_manipulation import phash, hamming_distance

# Panel must contain at least this fraction of non-background pixels to count.
MIN_CONTENT_RATIO = 0.05
# Minimum gap (fraction of the axis) to split on.
MIN_GAP_RATIO = 0.02
# Minimum panel size in pixels (either axis) to keep.
MIN_PANEL_DIM = 48
# Perceptual-hash hamming threshold for "near-duplicate" (tighter than the
# whole-figure threshold: grid tiles are smaller, so identity is more decisive).
DUPLICATE_THRESHOLD = 6
# Minimum figure dimension to attempt the grid fallback (western-blot panels
# are rarely separated by whitespace, so a 3x3 grid is used for large figures).
GRID_FALLBACK_MIN_DIM = 240
GRID_ROWS = 3
GRID_COLS = 3


def _content_mask(gray: np.ndarray, bg_threshold: int = 210) -> np.ndarray:
    """True where the pixel is likely content (non-near-white background)."""
    return gray < bg_threshold


def _split_axis(mask: np.ndarray, axis: int, size: int) -> list[tuple[int, int]]:
    """Split a 2-D mask along one axis by whitespace runs.

    Returns a list of (start, end) intervals along `axis` that contain content.
    `mask` is the full 2-D boolean array; `axis` is 0 (rows) or 1 (cols).
    """
    density = mask.mean(axis=1 - axis)  # fraction of content per row/col
    gap = density < 0.03
    min_gap = max(6, int(size * MIN_GAP_RATIO))

    # find [start, end) intervals of content separated by gaps >= min_gap
    intervals: list[tuple[int, int]] = []
    start: int | None = None
    gap_run = 0
    for i in range(size):
        if not gap[i]:
            if start is None:
                start = i
            gap_run = 0
        else:
            if start is not None:
                gap_run += 1
                if gap_run >= min_gap:
                    intervals.append((start, i - gap_run + 1))
                    start = None
                    gap_run = 0
    if start is not None:
        intervals.append((start, size))
    return intervals


def split_panels(
    img: Image.Image,
    min_gap_ratio: float = MIN_GAP_RATIO,
    min_panel: int = MIN_PANEL_DIM,
) -> list[tuple[str, Image.Image]]:
    """Split a figure image into panels via row/column whitespace projection.

    Returns [(panel_label, panel_image), ...] where labels are like "r1c2".
    A figure with no detectable internal whitespace structure yields a single
    panel (the figure itself).
    """
    gray = np.asarray(img.convert("L"), dtype=np.uint8)
    mask = _content_mask(gray)
    h, w = gray.shape

    # Grid-first strategy for large figures: western-blot / gel panels are
    # rarely separated by clean whitespace (bands create fine white slivers that
    # over-split), so a coarse 3x3 grid is a better panel prior. Whitespace
    # projection is still used for small figures and as the 'whole' fallback.
    if min(w, h) >= GRID_FALLBACK_MIN_DIM:
        rows, cols = GRID_ROWS, GRID_COLS
        cw, ch = w // cols, h // rows
        panels = []
        for r in range(rows):
            for c in range(cols):
                tile = img.crop((c * cw, r * ch, min(w, (c + 1) * cw), min(h, (r + 1) * ch)))
                tmask = _content_mask(np.asarray(tile.convert("L"), dtype=np.uint8))
                if tmask.sum() / max(1, tmask.size) < MIN_CONTENT_RATIO:
                    continue  # mostly empty corner: skip (all-white tiles hash identically)
                panels.append((f"r{r + 1}c{c + 1}", tile))
        if panels:
            return panels

    row_bands = _split_axis(mask, axis=0, size=h)
    panels: list[tuple[str, Image.Image]] = []
    for ri, (r0, r1) in enumerate(row_bands, start=1):
        band_mask = mask[r0:r1, :]
        col_bands = _split_axis(band_mask, axis=1, size=w)
        for ci, (c0, c1) in enumerate(col_bands, start=1):
            pw, ph = c1 - c0, r1 - r0
            if pw < min_panel or ph < min_panel:
                continue
            crop = band_mask[:, c0:c1]
            if crop.sum() / max(1, crop.size) < MIN_CONTENT_RATIO:
                continue  # mostly empty margin
            panels.append((f"r{ri}c{ci}", img.crop((c0, r0, c1, r1))))

    return panels or [("whole", img.copy())]


def detect_panel_reuse(
    images: dict[str, Image.Image],
    threshold: int = DUPLICATE_THRESHOLD,
) -> list[dict]:
    """Find near-duplicate panels across *different* source locations.

    Compares panel hashes for all figures in `images`. A pair is reported when
    their perceptual hashes differ by <= `threshold` and the two panels do NOT
    come from the same crop of the same figure (i.e. they are from different
    figures, or from different panels of the same figure).

    Returns a list of dicts:
        {"figure_a", "panel_a", "figure_b", "panel_b", "distance"}
    """
    panels: list[dict] = []  # each: {figure, panel, hash}
    for fig_id, img in images.items():
        for label, panel in split_panels(img):
            panels.append({"figure": fig_id, "panel": label, "hash": phash(panel)})

    pairs: list[dict] = []
    for i in range(len(panels)):
        for j in range(i + 1, len(panels)):
            a, b = panels[i], panels[j]
            if a["figure"] == b["figure"] and a["panel"] == b["panel"]:
                continue
            dist = hamming_distance(a["hash"], b["hash"])
            if dist <= threshold:
                pairs.append({
                    "figure_a": a["figure"],
                    "panel_a": a["panel"],
                    "figure_b": b["figure"],
                    "panel_b": b["panel"],
                    "distance": dist,
                })
    return pairs
