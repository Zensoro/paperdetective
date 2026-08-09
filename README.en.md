**English** | [**简体中文**](README.md)
# 🔍 PaperDetective

**Content-level academic-integrity screener** — scans research papers for six families of research-integrity signals: data fabrication, image manipulation, citation fraud, retraction flags, internal inconsistency, and cross-paper duplication. Outputs a strictly-schema'd structured report.

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-111%20passed-brightgreen)](#-tests)
[![CI](https://github.com/Zensoro/paperdetective/actions/workflows/ci.yml/badge.svg)](https://github.com/Zensoro/paperdetective/actions/workflows/ci.yml)

> ⚖️ **Disclaimer**: results are **screening signals**, not forensic proof. False positives and false negatives are possible; do not use this tool as the sole basis for accusing a paper or author of misconduct. Always corroborate with domain experts.

---

## ✨ Features

| Module | Method | Evidence level | Mode |
| --- | --- | --- | --- |
| Data fabrication | **GRIM** (mean × sample-size integer consistency), Benford's first-digit law, p-curve | Hard / Soft | 🆓 Free |
| Image manipulation | pHash perceptual hashing (whole-figure reuse), **RegionReuse** (panel-level reuse via multi-scale grids + texture filtering + tiered thresholds), ELA error-level analysis, **BandELA** (per-lane error analysis), **LaneReuse** (lane-level duplication via Pearson-correlation + pixel-diff double gate) | Hard / Soft | 🆓 Free |
| Cross-paper duplication | Cross-document pHash comparison, data fingerprints | Hard | 🆓 Free |
| Citation fraud | DOI format check + doi.org existence resolution | Hard | 💎 PRO |
| Retraction flags | Retraction keyword / metadata cross-check (pluggable) | Hard | 💎 PRO |
| Internal inconsistency | Relative-deviation comparison of numerical claims (NLI pluggable) | Soft | 🆓 Free |

- **Deterministic algorithms** — every conclusion comes from deterministic rules; no free-form model inference, no hallucination risk.
- **Case-driven development** — detectors are iterated against officially confirmed fraud cases (ORI / Rice investigation / Pfizer statements); the [8-case verification matrix](docs/case-studies/corpus-2026-08.en.md) ensures high-confidence hits land on officially confirmed locations. **Independent control papers** (method/meta-analysis papers with no WB figures, never used in tuning) validate the false-positive rate.
- **Layered confidence engine** — hard evidence ≥ 0.85; soft signals corroborated; internal knowledge capped at 0.60.
- **Strict schema** — Pydantic-validated JSON report; pretty Markdown export.
- **Batch processing** — directory input; one file failing won't break the batch.
- **Offline by default** — the free tier runs entirely locally. Networked PRO checks live in the optional `paperdetective-pro` extension.

## 🚀 Install

```bash
pip install -e .                # core
pip install -e ".[pdf,docx]"    # PDF / Word support
pip install -e ".[dev]"         # development (pytest)
# All capabilities (incl. DOI check & retraction scan) are free and open source
```

> 📖 **Fully free & open source**: all capabilities (including DOI existence check and retraction scanning) are MIT-licensed and shipped in this repo.

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
├── plugins.py           # Extension loader (entry-point, backward compat)
├── eval.py              # gold-annotation evaluation (precision/recall/F1)
├── detect/              # data fabrication · image manipulation · internal inconsistency · cross-paper
└── engine/              # confidence · arbitration · triangle verification
```

The former paid extension `paperdetective-pro` is archived; its DOI check and retraction scan are merged into this free core. Old extensions still load via the `paperdetective.pro` entry-point (backward compatible).

## ✅ Tests

```bash
python -m pytest        # 111 tests
```

## 📚 Corpus

Detectors are driven by **officially confirmed** real fraud cases (case-driven development):

| Case | Source | RegionReuse hit | LaneReuse hit |
| --- | --- | --- | --- |
| Brand et al. 2013 (HER3 western-blot) | ORI | ✅ Fig6↔Fig7 d=0 exact duplicate | ✅ 15 clusters (51 pairs) cross-figure |
| Lukianova-Hleb et al. 2012 (plasmonic nanobubbles) | Rice investigation | ✅ Fig3 internal duplicates | ✅ 4 clusters |
| Yin et al. 2012 (PDK-1) | Pfizer statement | ✅ Fig1/Fig2 cross-figure duplicate | ✅ 2 clusters |
| Yin & Nassirpour 2013 (miR-221) | Pfizer statement | ⚠️ MISS (lane-level duplication misaligned with grid) | ✅ **2 clusters** (Fig6 b6 lanes 2/5/8 triple + 3/9) |
| Bo-Yu et al. 2014 (ANGPTL4) | ORI | ✅ | ✅ 15 clusters (38 pairs; biggest 11 lanes across 3 figures) |
| Bo-Yu et al. 2013 (dendritic) | ORI | ✅ | ✅ 12 clusters |
| Lipid 2014 (PLoS ONE 11:111253) | retracted | ✅ | ✅ 1 cluster |
| ZMARF 2014 (PLoS ONE 9:94830) | retracted | ✅ | ✅ 13 clusters |

**LaneReuse hits 8/8** — including the case RegionReuse missed: the "duplicated bands
inside western blots" Pfizer confirmed for miR-221 (Fig6 lane triple) is caught by
lane-level comparison. Control set (3 method/meta-analysis papers without WB figures,
independent of tuning): **zero false positives**.

→ Full matrix, hit/miss analysis, and reproduction commands:
[docs/case-studies/corpus-2026-08.en.md](docs/case-studies/corpus-2026-08.en.md)

## 📖 Case study

See [docs/case-studies/her3-brand-2013.md](docs/case-studies/her3-brand-2013.md) for a worked example: PaperDetective (free tier) run against **Brand et al. 2013** (PLoS ONE 8:e71518), a paper officially flagged by the **U.S. Office of Research Integrity (ORI)** for falsified western-blot data — plus the honest findings + caveats + a PDF-ingestion improvement suggestion.

## 🗺️ Roadmap

- [x] CI (GitHub Actions, green)
- [x] Automatic embedded-image extraction from PDFs (v0.4.0, incl. page-furniture auto-filter)
- [x] RegionReuse panel-level image forensics (v0.4.0 — caught the ORI-confirmed fabrication in the [case study](docs/case-studies/her3-brand-2013.md))
- [x] RegionReuse v2: multi-scale grids + texture filtering + tiered thresholds (v0.5.0 — 7/8 hits on the [fraud corpus](docs/case-studies/corpus-2026-08.en.md))
- [x] BandELA per-lane error-level analysis (v0.4.0)
- [x] LaneReuse lane-level duplication detection (v0.6.0 — corr + pixel-diff gates, hit clustering, control-set validation; 8/8 fraud hits)
- [ ] Full SPRITE integration into the pipeline
- [ ] PRO: Retraction-database cross-check (Retraction Watch / Crossref)
- [ ] PRO: NLI-based internal-inconsistency (pluggable LLM)
- [ ] PRO: HTML / PDF report export
- [ ] Web UI

## 🤖 Development & AI disclosure

This project is developed with **heavy AI assistance** (code generation, tests,
docs, refactoring, code review — commit history includes "Kimi review fixes").
Commitments:

- **Core algorithms & thresholds are human-reviewed** (GRIM/SPRITE/Benford/
  pHash/ELA/LaneReuse logic and parameter values), not machine-asserted.
- **Self-evaluation limits are disclosed**: the 8-case hits, control-group
  errors etc. come from the author's own pipeline with no independent
  reproduction yet; the 3-paper control group lacks statistical power, so
  "zero false positives" means "none found in self-testing", not a statistical
  guarantee.
- **Public-trust commitment**: if you find any overstated claim, please open an
  issue — accuracy over hype.

## 📄 License

MIT — see [LICENSE](LICENSE). All detection capabilities (including DOI check and retraction scan) are free and open source.

## 📚 Citation / Press

- Brand et al. 2013 (PLoS ONE 8:e71518) — case study: [docs/case-studies/her3-brand-2013.md](docs/case-studies/her3-brand-2013.md)
- Fraud corpus 2026-08 (8 officially confirmed cases): [docs/case-studies/corpus-2026-08.en.md](docs/case-studies/corpus-2026-08.en.md)
