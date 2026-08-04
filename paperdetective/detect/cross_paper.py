"""Cross-paper duplication detection (image reuse + data fingerprints)."""
from __future__ import annotations

import hashlib
import numpy as np
from .image_manipulation import hamming_distance, phash


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


def find_cross_paper_duplicates(
    papers: dict[str, dict], threshold: int = 8
) -> list[tuple[str, str, str]]:
    """Return (image_id_a, image_id_b, "cross-paper") for reused images across papers.

    image_id_a / image_id_b are prefixed as "{paper_id}:{img_id}" so the
    originating paper is identifiable (e.g. "paperA:fig1", "paperB:fig2").
    Only pairs spanning *different* papers are reported; each image is
    hashed exactly once regardless of how many papers are compared.
    """
    hashes: dict[str, str] = {}
    for paper_id, artifacts in papers.items():
        for img_id, img in artifacts.get("images", {}).items():
            hashes[f"{paper_id}:{img_id}"] = phash(img)
    result = []
    keys = list(hashes)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            if a.split(":", 1)[0] == b.split(":", 1)[0]:
                continue  # same-paper reuse is not a cross-paper finding
            if hamming_distance(hashes[a], hashes[b]) <= threshold:
                result.append((a, b, "cross-paper"))
    return result
