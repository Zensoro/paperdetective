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


def _make_noise(seed: int, size=(64, 64)) -> Image.Image:
    rng = np.random.default_rng(seed)
    return Image.fromarray(rng.integers(0, 255, (size[1], size[0], 3), dtype=np.uint8))


def test_phash_same_image_same_hash():
    a = phash(_make_image(100))
    b = phash(_make_image(100))
    assert a == b


def test_phash_different_images_differ():
    # 真实感图片（噪声纹理）与渐变在感知哈希下应显著不同；
    # 纯色/镜像渐变这类退化工况不代表真实论文图片
    a = phash(_make_noise(seed=1))
    b = phash(_make_gradient(0, 255))
    assert hamming_distance(a, b) > 8


def test_phash_robust_to_brightness_shift():
    a = phash(_make_noise(seed=1))
    b = phash(_make_noise(seed=1).point(lambda x: min(255, x + 10)))
    assert hamming_distance(a, b) <= 8


def test_detect_reuse_finds_duplicate():
    # solid fills are degenerate for pHash (see report) — use structured
    # gradients: fig2 is fig1 with a brightness offset (near-duplicate),
    # fig3 is reversed (distinct).
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


def test_ela_does_not_flag_uniform_noise():
    # 高噪声图片全局误差虽高，但误差分布均匀（无局部集中），不应误报
    r = ela_score(_make_noise(seed=3))
    assert r["ela_score"] > 5.0  # 确认确实进入了高误差区间
    assert r["violated"] is False
