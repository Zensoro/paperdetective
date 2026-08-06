"""Band-level ELA: error-level analysis per horizontal strip (lane).

Whole-image ELA only sees manipulation that is anomalous relative to the whole
figure. Western-blot fabrication is often *band-level* — one lane is re-used,
moved, or spliced into a neighbouring lane. Running ELA per horizontal strip
keeps the spatial resolution that whole-figure ELA averages away.

In practice we flag a lane when either:
  - its standalone ELA check reports a violation (error concentrated in blocks),
    or
  - its mean re-encoding error is anomalously high relative to the figure's
    median lane error (a spliced/edited lane typically re-compresses with a
    different error signature than its untouched neighbours).

See docs/case-studies/her3-brand-2013.md for the motivating ORI-confirmed case.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .image_manipulation import ela_score

DEFAULT_N_BANDS = 10
# A lane must exceed the figure's median lane error by at least this multiple
# to be flagged as anomalous (2x is deliberately conservative).
ANOMALY_MULTIPLIER = 2.0
# Absolute floor: lanes with ELA below this are never flagged.
ANOMALY_ABS_FLOOR = 2.5


def split_bands(img: Image.Image, n_bands: int = DEFAULT_N_BANDS) -> list[Image.Image]:
    """Slice a figure into `n_bands` horizontal strips (lanes)."""
    w, h = img.size
    band_h = max(8, h // n_bands)
    return [img.crop((0, y, w, min(h, y + band_h))) for y in range(0, h, band_h)]


def band_ela_scan(img: Image.Image, n_bands: int = DEFAULT_N_BANDS) -> dict:
    """Run ELA on each horizontal lane; flag anomalous lanes.

    Returns:
        {
          "n_bands": int,
          "median_ela": float,
          "flagged": [ {band, y, ela_score, contrast, violated}, ... ],
        }
    """
    bands = split_bands(img, n_bands=n_bands)
    results = []
    for i, band in enumerate(bands):
        res = ela_score(band)
        results.append({
            "band": i,
            "y": i * band.size[1],
            "ela_score": res["ela_score"],
            "contrast": res["block_contrast"],
            "violated": res["violated"],
        })

    scores = np.array([r["ela_score"] for r in results], dtype=np.float64)
    median = float(np.median(scores)) if len(scores) else 0.0
    threshold = max(ANOMALY_ABS_FLOOR, ANOMALY_MULTIPLIER * median)
    flagged = [r for r in results if r["violated"] or r["ela_score"] > threshold]

    return {"n_bands": len(results), "median_ela": round(median, 3), "flagged": flagged}
