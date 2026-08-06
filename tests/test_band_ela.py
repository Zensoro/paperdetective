"""Band-level ELA: per-lane error level analysis."""
import numpy as np
from PIL import Image

from paperdetective.detect.band_ela import band_ela_scan, split_bands


def _synthetic_blot(size=(320, 240), noise=6):
    """A pseudo western blot: light background + dark horizontal lanes."""
    rng = np.random.default_rng(1)
    arr = np.full((size[1], size[0], 3), 235, dtype=np.uint8)
    for y in (40, 100, 160):
        arr[y:y + 18, :] = 60 + rng.integers(0, noise, (18, size[0], 3))
    return Image.fromarray(arr)


def test_split_bands_produces_strips():
    img = _synthetic_blot()
    bands = split_bands(img, n_bands=10)
    assert len(bands) == 10
    assert all(b.size[0] == img.size[0] for b in bands)


def test_band_ela_scan_reports_structure():
    img = _synthetic_blot()
    scan = band_ela_scan(img, n_bands=10)
    assert scan["n_bands"] == 10
    assert 0 <= scan["median_ela"] < 20
    assert isinstance(scan["flagged"], list)


def test_band_ela_scan_clean_image_not_overly_flagged():
    # plain gradient (no manipulation) should not trip the anomaly floor
    ramp = np.linspace(200, 255, 240, dtype=np.uint8)
    arr = np.repeat(ramp[:, None, None], 3, axis=2)
    arr = np.repeat(arr, 320, axis=1)
    scan = band_ela_scan(Image.fromarray(arr), n_bands=10)
    assert len(scan["flagged"]) == 0
