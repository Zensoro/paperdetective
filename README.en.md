**English** | [**简体中文**](README.md)
# 🔍 PaperDetective

**Content-level academic-integrity screener** — scans research papers for six families of research-integrity signals: data fabrication, image manipulation, citation fraud, retraction flags, internal inconsistency, and cross-paper duplication. Outputs a strictly-schema'd structured report.

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-97%20passed-brightgreen)](#-tests)
[![CI](https://github.com/Zensoro/paperdetective/actions/workflows/ci.yml/badge.svg)](https://github.com/Zensoro/paperdetective/actions/workflows/ci.yml)

> ⚖️ **Disclaimer**: results are **screening signals**, not forensic proof. False positives and false negatives are possible; do not use this tool as the sole basis for accusing a paper or author of misconduct. Always corroborate with domain experts.

---

## ✨ Features

| Module | Method | Evidence level | Mode |
| --- | --- | --- | --- |
| Data fabrication | **GRIM** (mean × sample-size integer consistency), Benford's first-digit law, p-curve | Hard / Soft | 🆓 Free |
| Image manipulation | pHash perceptual hashing (whole-figure reuse), **RegionReuse** (panel-level reuse via 3x3-grid + whitespace panel splitting), ELA error-level analysis, **BandELA** (per-lane error analysis) | Hard / Soft | 🆓 Free |
| Cross-paper duplication | Cross-document pHash comparison, data fingerprints | Hard | 🆓 Free |
| Citation fraud | DOI format check + doi.org existence resolution | Hard | 💎 PRO |
| Retraction flags | Retraction keyword / metadata cross-check (pluggable) | Hard | 💎 PRO |
| Internal inconsistency | Relative-deviation comparison of numerical claims (NLI pluggable) | Soft | 🆓 Free |

- **Deterministic algorithms** — every conclusion comes from deterministic rules; no free-form model inference, no hallucination risk.
- **Layered confidence engine** — hard evidence ≥ 0.85; soft signals corroborated; internal knowledge capped at 0.60.
- **Strict schema** — Pydantic-validated JSON report; pretty Markdown export.
- **Batch processing** — directory input; one file failing won't break the batch.
- **Offline by default** — the free tier runs entirely locally. Networked PRO checks live in the optional `paperdetective-pro` extension.

## 🚀 Install

```bash
pip install -e .                # core
pip install -e ".[pdf,docx]"    # PDF / Word support
pip install -e ".[dev]"         # development (pytest)
pip install paperdetective-pro  # paid extension (unlocks --pro networked checks)
```

> 🔒 **Open-core / paid split**: this repo (MIT) ships the free core. Networked checks (DOI resolution, retraction cross-check, NLI, batch, HTML/PDF export) live in the private extension `paperdetective-pro`, loaded via the `paperdetective.pro` entry-point; if not installed, `--pro` gracefully degrades to free mode.

## 📖 Quick start

```bash
# Analyze a single file (JSON output)
paperdetective analyze --input paper.pdf

# Batch-analyze a whole directory to a Markdown report
paperdetective analyze --input ./papers/ --markdown --output report.md

# PRO mode: enable networked DOI existence checks
paperdetective analyze --input paper.pdf --pro
```

Supported formats: `.txt` / `.pdf` / `.docx` / `.png` / `.jpg` / `.jpeg` / `.gif` / `.bmp`

### Python API

```python
from paperdetective.ingest import ingest_path
from paperdetective.analyze import run_detection
from paperdetective.report import to_markdown

docs = [ingest_path("paper.pdf")]
result = run_detection(docs, pro=False)
print(to_markdown(result))
```

### GRIM at a glance

Integer-valued data (e.g., Likert scales) must satisfy mean × sample-size = sum integer consistency. A reported `mean=2.66, n=2` can only come from sum 5 or 6 (mean 2.5 or 3.0); 2.66 is mathematically impossible — **GRIM violation (hard evidence, confidence 0.90)**.

## 🏗️ Architecture

```
Input (PDF / Word / image / text, batch supported)
    ↓
Phase A: ingest.py          — text + image extraction → Document
    ↓
Phase B: detect/            — six detectors (pure functions, independently testable)
         engine/            — confidence layering · method-conflict arbitration · triangle verification
    ↓
Phase C: analyze.py → report.py — pipeline orchestration; JSON / Markdown output
```

```
paperdetective/
├── ingest.py            # input extraction (txt/pdf/docx/image)
├── analyze.py           # pipeline orchestration
├── report.py            # Markdown renderer
├── schemas.py           # Pydantic report schema
├── plugins.py           # Pro extension loader (entry-point)
├── eval.py              # gold-annotation evaluation (precision/recall/F1)
├── detect/              # data fabrication · image manipulation · internal inconsistency · cross-paper
└── engine/              # confidence · arbitration · triangle verification
```

Pro extensions live in their own repo (`paperdetective-pro`, private/paid). Once registered via the `paperdetective.pro` entry-point, they auto-plug into the pipeline.

## ✅ Tests

```bash
python -m pytest        # 86 tests
```

## 📖 Case study

See [docs/case-studies/her3-brand-2013.md](docs/case-studies/her3-brand-2013.md) for a worked example: PaperDetective (free tier) run against **Brand et al. 2013** (PLoS ONE 8:e71518), a paper officially flagged by the **U.S. Office of Research Integrity (ORI)** for falsified western-blot data — plus the honest findings + caveats + a PDF-ingestion improvement suggestion.

## 🗺️ Roadmap

- [x] CI (GitHub Actions, green)
- [x] Automatic embedded-image extraction from PDFs (v0.4.0, incl. page-furniture auto-filter)
- [x] RegionReuse panel-level image forensics (v0.4.0 — caught the ORI-confirmed fabrication in the [case study](docs/case-studies/her3-brand-2013.md))
- [x] BandELA per-lane error-level analysis (v0.4.0)
- [ ] Full SPRITE integration into the pipeline
- [ ] PRO: Retraction-database cross-check (Retraction Watch / Crossref)
- [ ] PRO: NLI-based internal-inconsistency (pluggable LLM)
- [ ] PRO: HTML / PDF report export
- [ ] Web UI

## 📄 License

MIT for this repo (free core) — see [LICENSE](LICENSE).

Networked paid capabilities (DOI resolution, retraction cross-check, NLI, batch, report export) live in the private extension `paperdetective-pro` under a proprietary license and are NOT redistributed with this repo.

## 📚 Citation / Press

- Brand et al. 2013 (PLoS ONE 8:e71518) — case study: [docs/case-studies/her3-brand-2013.md](docs/case-studies/her3-brand-2013.md)
