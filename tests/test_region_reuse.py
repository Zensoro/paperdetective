"""Region-level image forensics: panel-split perceptual hashing."""
import numpy as np
from PIL import Image

from paperdetective.detect.region_reuse import (
    split_panels,
    detect_panel_reuse,
)


def _make_white_bg(fill, size=(200, 100)):
    """A white-background image with a solid content block (a pseudo 'panel')."""
    arr = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
    arr[20:80, 30:170] = fill  # content rectangle
    return Image.fromarray(arr)


def _make_textured(rng, size=(200, 100)):
    """White-background image with a textured content block (realistic-ish)."""
    arr = np.full((size[1], size[0], 3), 255, dtype=np.uint8)
    arr[20:80, 30:170] = rng.integers(40, 180, (60, 140, 3), dtype=np.uint8)
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
