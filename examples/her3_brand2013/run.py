"""Reproducibility wrapper for the Brand 2013 case study (PaperDetective >= 0.4.0).

Downloads the original PLoS article PDF if not already present, then runs the
free-tier pipeline *as-is*: the fixed `ingest_path` extracts embedded figures
AND auto-filters the shared full-page rasters that journal "printable" PDFs
embed on every page (previously a 100+ false-positive cascade).

Usage:
    python run.py            # writes report.json + report.md alongside this script
"""
from __future__ import annotations
import sys, urllib.request
from pathlib import Path

from paperdetective.ingest import ingest_path
from paperdetective.analyze import run_detection
from paperdetective.report import to_markdown

HERE = Path(__file__).parent
PDF  = HERE / "paper.pdf"
URL  = ("https://journals.plos.org/plosone/article/file?"
       "id=10.1371/journal.pone.0071518&type=printable")

if not PDF.exists():
    print(f"downloading {URL} -> {PDF} ...", file=sys.stderr)
    urllib.request.urlretrieve(URL, PDF)

doc = ingest_path(str(PDF))  # 0.4.0: extracts figures + drops page furniture
print(f"ingested {len(doc.images)} figure images from PDF", file=sys.stderr)
result = run_detection([doc], pro=False)

(HERE / "report.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
(HERE / "report.md"  ).write_text(to_markdown(result), encoding="utf-8")
print(f"wrote {HERE/'report.json'} and {HERE/'report.md'}", file=sys.stderr)

finds = result.detected_findings
print(f"detectors_run: {result.analysis_metadata.get('detectors_run')}")
print(f"findings: {len(finds)}")
for f in finds:
    print(f"  [{f.severity}] {f.detection_method} conf={f.confidence_score} | {f.title}")
    for e in f.evidence_pack[:1]:
        print(f"      {e.quote[:110]}")
