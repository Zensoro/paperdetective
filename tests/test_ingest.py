"""Ingest tests: text + image extraction from various formats."""
import io

import numpy as np
import pytest
from PIL import Image

from paperdetective.ingest import extract_images, ingest_path, ingest_text


def test_ingest_text():
    doc = ingest_text("实验测得 mean=12.3, n=40", paper_id="p1")
    assert doc.paper_id == "p1"
    assert "mean=12.3" in doc.text
    assert doc.images == []


def test_extract_images_from_png():
    buf = io.BytesIO()
    Image.fromarray(np.full((16, 16, 3), 100, dtype=np.uint8)).save(buf, "PNG")
    buf.seek(0)
    images = extract_images(io.BytesIO(buf.getvalue()), format="png")
    assert len(images) == 1


def test_ingest_path_plain_text(tmp_path):
    f = tmp_path / "paper.txt"
    f.write_text("这是纯文本论文 数据 12.3")
    doc = ingest_path(str(f))
    assert "12.3" in doc.text


def test_ingest_path_unsupported_raises(tmp_path):
    f = tmp_path / "paper.xyz"
    f.write_text("unsupported")
    with pytest.raises(ValueError):
        ingest_path(str(f))


def test_filter_furniture_drops_page_raster_and_keeps_figures():
    """page furniture (same content on every page) must be dropped."""
    import numpy as np
    from paperdetective.ingest import _filter_furniture
    # simulate: 3 pages, same 2000x3000 raster on each page + 2 distinct figures
    rng = np.random.default_rng(3)
    page_img = Image.fromarray(np.full((300, 200, 3), 255, dtype=np.uint8))
    fig_a = Image.fromarray(rng.integers(0, 255, (200, 200, 3), dtype=np.uint8))
    fig_b = Image.fromarray(rng.integers(0, 255, (200, 200, 3), dtype=np.uint8))
    images = [
        ("page1_X0.png", page_img), ("page1_Im1.png", fig_a),
        ("page2_X0.png", page_img), ("page2_Im2.png", fig_b),
        ("page3_X0.png", page_img),
    ]
    kept = _filter_furniture(images)
    ids = [i for i, _ in kept]
    assert "page1_X0.png" not in ids and "page2_X0.png" not in ids
    assert "page1_Im1.png" in ids and "page2_Im2.png" in ids
