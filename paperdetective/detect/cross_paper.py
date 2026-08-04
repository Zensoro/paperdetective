"""Cross-paper duplication detection (image reuse + data fingerprints)."""
from __future__ import annotations

import hashlib
import numpy as np
from .image_manipulation import detect_reuse


def data_fingerprint(arr: np.ndarray, n_bits: int = 256) -> str:
    """Hash of normalized histogram -> robust to small perturbations."""
    flat = np.asarray(arr, dtype=np.float64).ravel()
    if flat.size == 0:
        return hashlib.sha256(b"empty").hexdigest()
    hist, _ = np.histogram(flat, bins=8, density=True)
    hist = np.round(hist, 6)
    return hashlib.sha256(hist.tobytes()).hexdigest()


def match_data_fingerprints(papers: dict[str, dict]) -> list[tuple[str, str]]:
    seen: dict[str, str] = {}
    dups = []
    for paper_id, artifacts in papers.items():
        for fp in artifacts.get("data", []):
            if fp in seen and seen[fp] != paper_id:
                dups.append((seen[fp], paper_id))
            else:
                seen[fp] = paper_id
    return dups


def find_cross_paper_duplicates(papers: dict[str, dict]) -> list[tuple[str, str, str]]:
    """Return (paperA, paperB, image_id) for reused images across papers."""
    result = []
    keys = list(papers)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            images = {}
            for k in (keys[i], keys[j]):
                for img_id, img in papers[k].get("images", {}).items():
                    images[f"{k}:{img_id}"] = img
            for a, b in detect_reuse(images):
                result.append((a, b, "cross-paper"))
    return result
