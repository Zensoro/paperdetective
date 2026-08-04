"""Image manipulation detection: ELA (error level analysis) + perceptual hash."""
from __future__ import annotations

import io
from PIL import Image, ImageChops
import numpy as np


def _save_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


def ela_score(img: Image.Image) -> dict:
    """Error Level Analysis: re-save at 90% and measure diff."""
    img = img.convert("RGB").resize((256, 256))
    buf = _save_jpeg(img, 90)
    reencoded = Image.open(io.BytesIO(buf)).convert("RGB")
    diff = ImageChops.difference(img, reencoded)
    arr = np.asarray(diff, dtype=np.float32)
    score = round(float(arr.mean()), 3)
    return {
        "ela_score": score,
        "max_diff": int(arr.max()),
        # clean re-encodes < 1% mean error; higher = manipulation signal
        "violated": bool(score > 5.0),
    }


def phash(img: Image.Image, hash_size: int = 16) -> str:
    """Perceptual hash via DCT low-frequency comparison."""
    img = img.convert("L").resize((hash_size, hash_size))
    arr = np.asarray(img, dtype=np.float64)
    dct = np.zeros((hash_size, hash_size))
    for u in range(hash_size):
        for v in range(hash_size):
            # orthogonal DCT-II normalization: 1/sqrt(2) for zero freq,
            # 1.0 otherwise — keeps hash compatible with imagehash libs
            cu = 1.0 / np.sqrt(2) if u == 0 else 1.0
            cv = 1.0 / np.sqrt(2) if v == 0 else 1.0
            s = 0.0
            for x in range(hash_size):
                for y in range(hash_size):
                    s += arr[x, y] * np.cos((2*x+1)*u*np.pi/(2*hash_size)) * np.cos((2*y+1)*v*np.pi/(2*hash_size))
            dct[u, v] = 2 * cu * cv * s / (hash_size * hash_size)
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
