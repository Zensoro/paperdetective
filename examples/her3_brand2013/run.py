"""Reproducibility wrapper for the Brand 2013 case study.

Downloads the original PLoS article PDF if not already present, filters out
shared full-page rasters + logos (paperdetective ingestion limitation discovered
during this case study), then runs the full free-tier detector pipeline.

Usage:
    python run.py            # writes report.json + report.md alongside this script
"""
from __future__ import annotations
import io, sys, urllib.request
from pathlib import Path
from pypdf import PdfReader
from PIL import Image
from paperdetective.ingest import Document
from paperdetective.analyze import run_detection
from paperdetective.report import to_markdown

HERE = Path(__file__).parent
PDF  = HERE / "paper.pdf"
URL  = ("https://journals.plos.org/plosone/article/file?"
       "id=10.1371/journal.pone.0071518&type=printable")

if not PDF.exists():
    print(f"downloading {URL} -> {PDF} ...", file=sys.stderr)
    urllib.request.urlretrieve(URL, PDF)

reader = PdfReader(str(PDF))
text   = "\n".join((p.extract_text() or "") for p in reader.pages)
# Filter out shared full-page rasters + tiny logos (PLoS printable quirk)
images = []
for pi, page in enumerate(reader.pages):
    for im in page.images:
        name = im.name
        if name.startswith("X0") or name.startswith("Form"):
            continue
        try:
            images.append((f"p{pi+1}_{name}", Image.open(io.BytesIO(im.data)).convert("RGB")))
        except Exception:
            pass

print(f"text {len(text)} chars; substantive figures {len(images)}", file=sys.stderr)
doc = Document(paper_id="her3_brand2013", text=text, images=images)
result = run_detection([doc], pro=False)

(HERE / "report.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
(HERE / "report.md"  ).write_text(to_markdown(result), encoding="utf-8")
print(f"wrote {HERE/'report.json'} and {HERE/'report.md'}", file=sys.stderr)

finds = result.detected_findings
print(f"detectors_run: {result.analysis_metadata.get('detectors_run')}")
print(f"findings: {len(finds)}")
for f in finds:
    print(f"  [{f.severity}] {f.detection_method} conf={f.confidence_score} | {f.title}")
