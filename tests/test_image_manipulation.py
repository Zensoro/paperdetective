"""Image manipulation detection: ELA + perceptual hash."""
from PIL import Image
import numpy as np
from paperdetective.detect.image_manipulation import ela_score, phash, hamming_distance, detect_reuse


def _make_image(fill: int, size=(64, 64)) -> Image.Image:
    arr = np.full((size[1], size[0], 3), fill, dtype=np.uint8)
    return Image.fromarray(arr)


def _make_gradient(lo: int, hi: int, size=(64, 64)) -> Image.Image:
    ramp = np.linspace(lo, hi, size[1], dtype=np.uint8)
    arr = np.repeat(ramp[:, None, None], 3, axis=2)
    arr = np.repeat(arr, size[0], axis=1)
    return Image.fromarray(arr)


def test_phash_same_image_same_hash():
    a = phash(_make_image(100))
    b = phash(_make_image(100))
    assert a == b


def test_phash_different_images_differ():
    a = phash(_make_image(10))
    b = phash(_make_image(250))
    assert hamming_distance(a, b) > 8


def test_detect_reuse_finds_duplicate():
    # solid fills are degenerate for pHash (see report) — use structured
    # gradients: fig2 is fig1 shifted by 1 (near-duplicate), fig3 distinct.
    imgs = {"fig1": _make_gradient(0, 255), "fig2": _make_gradient(1, 255), "fig3": _make_gradient(255, 0)}
    pairs = detect_reuse(imgs, threshold=8)
    assert any({"fig1", "fig2"} == set(p) for p in pairs)


def test_ela_low_on_clean_image():
    img = _make_image(128)
    score = ela_score(img)
    assert score["ela_score"] <= 5.0


def test_ela_reports_violated_false_on_clean_image():
    # uniform fill re-encodes cleanly: no manipulation signal
    r = ela_score(_make_image(128))
    assert r["violated"] is False
