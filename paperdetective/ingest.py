"""Phase A input ingestion: PDF/Word/image/text -> Document."""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image


@dataclass
class Document:
    paper_id: str
    text: str = ""
    images: list = field(default_factory=list)  # [(image_id, PIL.Image)]
    tables: list = field(default_factory=list)  # [dict]

    def image_ids(self) -> list[str]:
        return [i[0] for i in self.images]


def ingest_text(text: str, paper_id: str = "doc") -> Document:
    return Document(paper_id=paper_id, text=text)


def extract_images(data, format: str = "png", prefix: str = "img") -> list[tuple[str, Image.Image]]:
    with Image.open(data) as img:
        return [(f"{prefix}0", img.copy())]


def ingest_path(path: str) -> Document:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".txt":
        return ingest_text(p.read_text(encoding="utf-8", errors="ignore"), paper_id=p.stem)
    if suffix in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
        with Image.open(p) as img:
            return Document(paper_id=p.stem, images=[(p.stem, img.copy())])
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            return Document(paper_id=p.stem, text="[PDF support requires: pip install paperdetective[pdf]]")
        reader = PdfReader(str(p))
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        return Document(paper_id=p.stem, text=text)
    if suffix == ".docx":
        try:
            import docx
        except ImportError:
            return Document(paper_id=p.stem, text="[Word support requires: pip install paperdetective[docx]]")
        d = docx.Document(str(p))
        text = "\n".join(par.text for par in d.paragraphs)
        return Document(paper_id=p.stem, text=text)
    if suffix == ".doc":
        raise ValueError("legacy .doc is not supported; please convert to .docx first")
    raise ValueError(f"unsupported file type: {suffix}")
