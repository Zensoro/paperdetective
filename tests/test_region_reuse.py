"""Region-level image forensics: panel-split perceptual hashing."""
import numpy as np
from PIL import Image

from paperdetective.detect.region_reuse import (
    split_panels,
    detect_panel_reuse,
    _pair_threshold,
    FINE_GRID_THRESHOLD,
    DUPLICATE_THRESHOLD,
    TEXTURE_MIN_STD,
)


def _make_white_bg(fill, size=(200, 100)):
    """A white-background image with a solid content block (a pseudo 'panel')."""
    arr = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
    arr[20:80, 30:170] = fill  # content rectangle
    return Image.fromarray(arr)


def _make_textured(rng, size=(200, 100)):
    """White-background image with a textured content block (realistic-ish)."""
    w, h = size
    arr = np.full((h, w, 3), 255, dtype=np.uint8)
    # content block inset by ~15% on each side
    x0, x1 = int(w * 0.15), int(w * 0.85)
    y0, y1 = int(h * 0.2), int(h * 0.8)
    arr[y0:y1, x0:x1] = rng.integers(40, 180, (y1 - y0, x1 - x0, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def test_split_panels_splits_on_whitespace():
    # two content blocks separated by a wide white gap -> 2 panels
    arr = np.full((100, 400, 3), 255, dtype=np.uint8)
    arr[20:80, 20:150] = 60   # left block
    arr[20:80, 250:380] = 120  # right block
    img = Image.fromarray(arr)
    panels = split_panels(img)
    assert len(panels) >= 2, f"expected >=2 panels, got {len(panels)}"


def test_split_panels_whole_figure_fallback():
    # fully-content image with no whitespace structure -> single 'whole' panel
    img = _make_white_bg(50, size=(80, 60))
    panels = split_panels(img)
    assert panels[0][0] == "whole"


def test_detect_panel_reuse_finds_cross_figure_duplicate():
    # same panel content embedded in two different figures
    rng = np.random.default_rng(7)
    block = _make_textured(rng, size=(180, 80))
    img_a = Image.new("RGB", (200, 100), (255, 255, 255))
    img_a.paste(block, (10, 10))
    img_b = Image.new("RGB", (200, 100), (255, 255, 255))
    img_b.paste(block, (10, 10))
    hits = detect_panel_reuse({"figA": img_a, "figB": img_b})
    assert any(h["figure_a"] != h["figure_b"] for h in hits)


def test_detect_panel_reuse_distinct_figures_no_hit():
    # distinct textured content should NOT hash as near-duplicates
    a = _make_textured(np.random.default_rng(1), size=(180, 80))
    b = _make_textured(np.random.default_rng(99), size=(180, 80))
    hits = detect_panel_reuse({"figA": a, "figB": b})
    assert hits == []


def test_grid_splits_drops_near_uniform_tiles():
    # v0.5.0: a large white image with ONE textured panel -> grid path must
    # drop the near-uniform white tiles (texture filter) and keep the textured one.
    rng = np.random.default_rng(3)
    img = Image.new("RGB", (400, 300), (255, 255, 255))
    img.paste(_make_textured(rng, size=(200, 200)), (10, 10))
    panels = split_panels(img)
    labels = [label for label, _ in panels]
    assert labels, "expected at least one textured tile from the grid path"
    # every kept tile must pass the texture gate (no pure-white corners)
    for _, tile in panels:
        gray = np.asarray(tile.convert("L"), dtype=np.float32)
        assert gray.std() >= TEXTURE_MIN_STD - 1e-6


def test_grid_finds_cross_figure_duplicate_large_images():
    # v0.5.0: duplicate panel embedded in two LARGE figures must be caught via
    # the multi-scale grid path (whitespace projection alone would miss it).
    rng = np.random.default_rng(11)
    block = _make_textured(rng, size=(160, 160))
    img_a = Image.new("RGB", (480, 320), (255, 255, 255))
    img_a.paste(block, (30, 30))
    img_b = Image.new("RGB", (480, 320), (255, 255, 255))
    img_b.paste(block, (30, 30))
    hits = detect_panel_reuse({"figA": img_a, "figB": img_b})
    assert any(h["figure_a"] != h["figure_b"] for h in hits), hits


def test_fine_grid_uses_stricter_threshold():
    # v0.5.0: pairs involving a 6x8 tile use FINE_GRID_THRESHOLD, others keep
    # the default — prevents the 6x8 false-positive explosion seen on Brand 2013.
    assert _pair_threshold("g6x8_1c1", "g3x3_1c1", DUPLICATE_THRESHOLD) == FINE_GRID_THRESHOLD
    assert _pair_threshold("g3x3_1c1", "g4x4_1c1", DUPLICATE_THRESHOLD) == DUPLICATE_THRESHOLD
    assert _pair_threshold("r1c1", "r2c2", DUPLICATE_THRESHOLD) == DUPLICATE_THRESHOLD
