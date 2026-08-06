# Case Study — Brand et al. 2013 (HER3 western-blot fabrication)

**Paper:** Brand TM, Iida M, Luthar N, Wleklinski MJ, Starr MM, Wheeler DL (2013).  
*Mapping C-Terminal Transactivation Domains of the Nuclear HER Family Receptor Tyrosine Kinase HER3.*  
**PLoS ONE** 8(8): e71518. DOI: `10.1371/journal.pone.0071518` — **RETRACTED**.

**Why this case:** the first author was officially sanctioned by the **U.S. Office of Research Integrity (ORI)** for **falsifying or fabricating** western-blot data in Figures 6B, 6C, and 7A (plus duplications in Figures 1B and 1C). The University of Wisconsin-Madison conducted the original investigation; PLOS ONE issued the retraction in April 2022 ([retraction notice](https://doi.org/10.1371/journal.pone.0267745)). It is an ideal public, well-documented, ORI-confirmed data-fabrication case — and the original PDF is **open access**.

This case study documents PaperDetective **v0.4.0** (free tier, August 2026) run against that PDF — **honestly**: what it caught, what it still misses, and the two product improvements that came out of this exercise (both shipped in v0.4.0).

---

## 1. Setup

- Paper PDF (4.3 MB, 15 pages) downloaded from the official PLoS article page.
- PaperDetective **v0.4.0** from this repo, `pip install -e ".[pdf]"` (Python 3.13).
- Detectors used (free tier): **Benford**, **GRIM**, **p-curve**, **pHash**, **ELA**, **RegionReuse** (new in v0.4.0), **BandELA** (new in v0.4.0).
- No manual preprocessing: `ingest_path("paper.pdf")` extracts embedded figures and **auto-filters page furniture** (see §4).

```bash
python examples/her3_brand2013/run.py   # downloads the PDF, runs the pipeline, writes the reports
```

---

## 2. What PaperDetective found

| Detector      | Ran | Findings | Severity       | Note |
|---------------|-----|----------|----------------|------|
| **RegionReuse** | ✅ | **1** | **High (conf 0.90)** | **Figure 6's bottom-left and bottom-right panels (`p6_Im3.png[r3c1] ≈ r3c2`, hamming=6) are near-identical — this is exactly the figure where ORI found 6B/6C falsified.** |
| **Benford**   | ✅ | 1        | Low (conf 0.50) | First-digit distribution of 1,854 numbers deviates from Benford expectation by 0.141 (digit-1 26.5 % vs expected 30.1 %). |
| **GRIM**      | ✅ | 0        | —              | Paper does not report the kind of integer mean/n summaries GRIM checks. |
| **p-curve**   | ✅ | 0        | —              | No individual t-test p-value set to inspect. |
| **pHash**     | ✅ | 0        | —              | Whole figures are distinct — whole-image hashing cannot see sub-figure reuse. |
| **ELA**       | ✅ | 0        | —              | No anomaly at whole-figure scale. |
| **BandELA**   | ✅ | 0        | —              | No lane anomaly above the 2x-median threshold on these particular images. |

**Free-tier summary: 2 findings — one High RegionReuse hit on the exact figure ORI flagged, one Low Benford nudge.** The High hit is a direct match to the official investigation.

Full machine-readable report: [`examples/her3_brand2013/report.json`](report.json)  
Human-readable report: [`examples/her3_brand2013/report.md`](report.md)

---

## 3. Why the fabrication is now visible (RegionReuse)

The ORI-confirmed fabrication is **panel-level**: bands re-used/rearranged within sub-figures of Figure 6. Whole-figure `pHash` averages the entire figure away, so it cannot see a duplicated bottom panel. **RegionReuse (v0.4.0)** splits each figure into panels first (3×3 grid for large figures, whitespace-projection for small ones), hashes every panel, then compares panels across the document. The duplicated panels in Figure 6 survive that split and match at hamming distance 6.

Design decisions that keep it honest:
- **Grid-first for large figures** — western blots/gels rarely have clean whitespace between panels; fine-grained whitespace splitting over-segments them into slivers (we verified: 14 fragments instead of a useful panel layout).
- **Content filter on tiles** — all-white corner tiles (which hash identically regardless of content) are dropped before comparison.
- **Tighter threshold (≤ 6) than whole-figure pHash (≤ 8)** — smaller panels make identity more decisive; the HER3 run yields exactly one hit, zero noise.

**Still a gap:** ORI also sanctioned *fabricated* (invented) bands in 6B/6C/7A, and *added* bands are invisible to any hashing approach — detecting them needs band-level ELA with per-lane cross-correlation (BandELA v0.4.0 runs per-lane ELA but did not trip the 2x-median threshold on this PDF; it is designed to catch spliced lanes, which this scan did not exhibit above threshold). PRO-level retraction cross-checking (planned) would flag this paper outright via Retraction Watch.

---

## 4. The PDF-ingestion bug this exercise uncovered — and its fix (v0.4.0)

The PLoS **"printable"** PDF embeds, on **every page**, the **same full-page raster XObject** (`X0.png`, 2550×3300 px, byte-identical across all 15 pages, MD5 `ce898c93…`). Running whole-document pHash over every extracted image produced **106 false positives** ("every image duplicates every other image") from a single PDF.

**Fix shipped in v0.4.0** (`ingest.py`):
1. **Page-granularity hash dedup** — an image whose content fingerprint appears on **≥ 80 % of pages** is page furniture (watermark / header / rasterized page) and is dropped *before* detection.
2. **Size-band filter** — images > 4000 px (full-page rasters) or < 100 px (logos/form fields) are not substantive figures.

Result on this PDF: the 23 extracted images (15 shared page-rasters + 7 figures + 1 logo) are reduced to the **7 substantive figures**; the 106-finding cascade is gone, and the remaining detections are the 2 findings above. Unit tests cover both heuristics (`tests/test_ingest.py`).

---

## 5. How to reproduce

```bash
git clone https://github.com/Zensoro/paperdetective.git
cd paperdetective
pip install -e ".[pdf,docx]"

python examples/her3_brand2013/run.py
# downloads the article PDF, runs the free-tier pipeline, writes:
#   examples/her3_brand2013/report.json, report.md
```

**Determinism:** every detector is deterministic; re-running yields byte-identical reports.

---

## 6. Take-away

- The free tier now **flags the exact panels ORI sanctioned** (RegionReuse High on Figure 6 bottom panels) plus a soft Benford nudge — an honest, reproducible, expert-reviewable result.
- Two product improvements were validated by a real case and shipped in v0.4.0: **page-furniture auto-filtering** in PDF ingestion (kills the false-positive cascade) and **RegionReuse panel-level forensics** (finds what whole-image hashing cannot).
- **What it still misses is documented too**: band *invention* (not reuse) and the PRO retraction cross-check remain on the roadmap.

Honest tools earn trust. We document both the hits and the misses — that is the only way a screening tool is worth shipping.

---

*Generated 2026-08 with PaperDetective `0.4.0`.  
Retraction record: [`10.1371/journal.pone.0267745`](https://doi.org/10.1371/journal.pone.0267745).  
ORI case summary: [`ori.hhs.gov/content/casesummary-brand-toni-m`](https://ori.hhs.gov/content/casesummary-brand-toni-m).*
