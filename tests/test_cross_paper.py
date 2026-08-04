"""Cross-paper duplication: image reuse and data fingerprint matching."""
import numpy as np
from PIL import Image
from paperdetective.detect.cross_paper import (
    data_fingerprint, match_data_fingerprints, find_cross_paper_duplicates,
)


def test_data_fingerprint_stable():
    a = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    b = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    assert a == b


def test_data_fingerprint_sensitive():
    a = data_fingerprint(np.array([1.0, 2.0, 3.0]))
    b = data_fingerprint(np.array([1.0, 2.0, 4.0]))
    assert a != b


def test_match_fingerprints_finds_duplicate():
    papers = {
        "paperA": {"data": [data_fingerprint(np.array([1, 2, 3]))]},
        "paperB": {"data": [data_fingerprint(np.array([1, 2, 3]))]},
    }
    dups = match_data_fingerprints(papers)
    assert len(dups) >= 1


def test_find_cross_paper_duplicates_images():
    arr = np.full((32, 32, 3), 120, dtype=np.uint8)
    img_a = Image.fromarray(arr)
    img_b = Image.fromarray(arr.copy())
    papers = {
        "paperA": {"images": {"fig1": img_a}},
        "paperB": {"images": {"fig2": img_b}},
    }
    dups = find_cross_paper_duplicates(papers)
    assert any("fig1" in str(d) and "fig2" in str(d) for d in dups)


def test_same_paper_reuse_is_not_cross_paper():
    # 同一篇论文内部的图片重复不应被标记为 cross-paper
    # （用噪声纹理而非纯色图，避免 pHash 退化工况）
    rng = np.random.default_rng(7)
    arr_a = rng.integers(0, 255, (32, 32, 3), dtype=np.uint8)
    arr_b = rng.integers(0, 255, (32, 32, 3), dtype=np.uint8)
    papers = {
        "paperA": {"images": {"fig1": Image.fromarray(arr_a),
                              "fig2": Image.fromarray(arr_a.copy())}},
        "paperB": {"images": {"fig9": Image.fromarray(arr_b)}},
    }
    assert find_cross_paper_duplicates(papers) == []
