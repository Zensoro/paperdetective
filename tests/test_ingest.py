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
