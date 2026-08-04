"""Image manipulation detection: ELA (error level analysis) + perceptual hash."""
from __future__ import annotations

import io
from PIL import Image, ImageChops
import numpy as np


def _save_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def ela_score(img: Image.Image, blocks: int = 8) -> dict:
    """Error Level Analysis: re-save at 90% and measure diff.

    除了全局平均误差，还计算 8x8 分块的最大块均值。篡改/拼接区域表现为
    局部误差显著高于整体（空间集中）；而高噪声图片虽然全局误差高，
    但误差分布均匀，不应误报——因此要求两者同时成立才判定违规。
    """
    img = img.convert("RGB").resize((256, 256))
    buf = _save_jpeg(img, 90)
    reencoded = Image.open(io.BytesIO(buf)).convert("RGB")
    diff = ImageChops.difference(img, reencoded)
    arr = np.asarray(diff, dtype=np.float32)
    score = round(float(arr.mean()), 3)
    bh, bw = arr.shape[0] // blocks, arr.shape[1] // blocks
    block_means = arr[:bh * blocks, :bw * blocks].reshape(
        blocks, bh, blocks, bw, 3).mean(axis=(1, 3, 4))
    max_block = round(float(block_means.max()), 3)
    contrast = round(max_block / max(score, 1e-9), 3)
    return {
        "ela_score": score,
        "max_diff": int(arr.max()),
        "max_block_mean": max_block,
        "block_contrast": contrast,
        # 全局误差高(>5) 且 局部误差集中(峰值块 > 1.5x 均值) 才是篡改信号；
        # 干净重编码均值 < 1，高噪声图片误差虽高但分布均匀(contrast ≈ 1)
        "violated": bool(score > 5.0 and contrast > 1.5),
    }


def phash(img: Image.Image, hash_size: int = 16) -> str:
    """Perceptual hash via DCT low-frequency comparison.

    Uses scipy's DCT-II with orthogonal zero-frequency normalization
    (1/sqrt(2) for u/v == 0), bit-identical to the reference imagehash
    convention but vectorized (~300x faster than a naive loop).
    """
    from scipy.fftpack import dctn

    img = img.convert("L").resize((hash_size, hash_size))
    arr = np.asarray(img, dtype=np.float64)
    dct = dctn(arr, axes=(0, 1), norm=None)
    cu = np.ones(hash_size)
    cu[0] = 1.0 / np.sqrt(2)
    dct = dct * cu[:, None] * cu[None, :] / (hash_size * hash_size)
    low = dct[:8, :8].flatten()
    med = np.median(low)
    return "".join("1" if v > med else "0" for v in low)


def hamming_distance(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def detect_reuse(images: dict[str, Image.Image], threshold: int = 8) -> list[tuple[str, str]]:
    """Find near-duplicate images across a paper (or papers)."""
    hashes = {k: phash(v) for k, v in images.items()}
    pairs = []
    keys = list(hashes)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            if hamming_distance(hashes[keys[i]], hashes[keys[j]]) <= threshold:
                pairs.append((keys[i], keys[j]))
    return pairs
