# Case Study — Brand et al. 2013 (HER3 western-blot fabrication)

**Paper:** Brand TM, Iida M, Luthar N, Wleklinski MJ, Starr MM, Wheeler DL (2013).  
*Mapping C-Terminal Transactivation Domains of the Nuclear HER Family Receptor Tyrosine Kinase HER3.*  
**PLoS ONE** 8(8): e71518. DOI: `10.1371/journal.pone.0071518` — **RETRACTED**.

**Why this case:** the first author was officially sanctioned by the **U.S. Office of Research Integrity (ORI)** for **falsifying or fabricating** western-blot data in Figures 6B, 6C, and 7A (plus duplications in Figures 1B and 1C). The University of Wisconsin-Madison conducted the original investigation; PLOS ONE issued the retraction in April 2022 ([retraction notice](https://doi.org/10.1371/journal.pone.0267745)). It is an ideal public, well-documented, ORI-confirmed data-fabrication case — and the original PDF is **open access**.

This case study documents what PaperDetective (free tier, August 2026) finds when run against that PDF **honestly** — including what it caught, what it missed, and a **product-improvement finding** we discovered while building this case.

---

## 1. Setup

- Paper PDF (4.3 MB, 15 pages) downloaded from the official PLoS article page.
- PaperDetective `0.3.0` installed from the repo (Python 3.13).
- Detectors used (free tier): **Benford**, **GRIM**, **p-curve**, **pHash** (within-paper image reuse), **ELA**.

### ⚠️ A caveat we had to work around (product-relevant)

The PLoS **"printable"** version of the article embeds, on **every page**, the **same full-page raster XObject** (`X0.png`, 2550 × 3300 px, byte-identical across all 15 pages, MD5 `ce898c93…`). The CLI's PDF ingestion (`ingest_path`) currently extracts every embedded image including those page rasters. If you naively compare all extracted images, pHash flags every pair as duplicated — 106 false positives from one PDF, **none of them real**.

For this case study we therefore ran PaperDetective with a **lightweight wrapper that filters out the shared page-rasters and the small form/logo images**, keeping only the seven substantive figures (Im1…Im7, one per Results figure). This wrapper (≈25 lines) lives at `examples/her3_brand2013/run.py` for reproducibility.

---

## 2. What PaperDetective found

Running on the wrapped Document (7 figure images + 72,362 chars of text):

| Detector    | Ran | Findings | Severity      | Note |
|-------------|-----|----------|---------------|------|
| **Benford** | ✅  | 1        | Low (conf 0.50) | First-digit distribution of 1,854 numbers deviates from Benford expectation by 0.141 (digit-1 frequency 26.5 % vs expected 30.1 %). |
| **GRIM**    | ✅  | 0        | —             | Paper does not report the kind of integer mean/n summaries GRIM checks (no Likert-style tables). |
| **p-curve** | ✅  | 0        | —             | Paper does not report p-values from individual t-tests that p-curve inspects (mostly ANOVA/structural biology). |
| **pHash**   | ✅  | 0        | —             | The seven **whole-figure images** are distinct — pHash finds no cross-figure duplication. *(See §3 — band-level reuse is not visible at the whole-figure scale.)* |
| **ELA**     | ✅  | 0        | —             | No anomaly clusters at the whole-figure scale. |

**Free-tier summary:** one soft Benford signal — honest and defensible.

Full machine-readable report: [`examples/her3_brand2013/report.json`](report.json)  
Human-readable report: [`examples/her3_brand2013/report.md`](report.md)

---

## 3. Why the western-blot fabrication was not flagged (and how it could be)

The ORI-confirmed fabrication is **band-level** — the same bands were re-used, rearranged, or invented within sub-panels of Figures 6 and 7. PaperDetective's `pHash` compares **whole figures**, so it cannot detect reuse of a sub-panel across figures, nor a band that was moved a few pixels within a panel. This is a real **product gap** for the free tier.

Two concrete improvements (ranked by ROI):

1. **Region-level image forensics** — split each figure into panels (sliding-window + layout detection), hash each panel separately, then compare panels across figures. Would have flagged Figure 1B ↔ 1C (within-paper duplication) and likely 6B/6C/7A band-level reuse.
2. **Band-level ELA on each detected panel** — error-level analysis per band lane (not per whole figure), with cross-band correlation. Would catch the fabrication even when bands are *added* (ELA spike at the seam between original and inserted regions).

PRO-level checks would also have flagged this paper via the **retraction cross-check** feature: a publication-date-vs-retraction-date lookup against the Retraction Watch database (planned for `paperdetective-pro`).

---

## 4. A PDF-ingestion improvement we discovered

The **printable** PDF format PLoS serves embeds, on every page, the **same full-page raster XObject** (verified: all 15 `X0.png` files byte-identical, same MD5). The current `ingest_path` returns all embedded images including those page rasters. With whole-doc pHash that becomes a flood of "every image duplicates every other image" — a 106-finding false-positive cascade from a single PDF.

**Recommended fix:** in `ingest.py`, **detect and skip shared page-furniture images** before returning them to the detector. Two cheap heuristics work well in practice:

- **Hash dedup across the document** — drop any image whose MD5/SHA appears on ≥ 80 % of pages (page furniture, watermarks, logos).
- **Size-band filter** — drop images larger than e.g. 4 000 × 4 000 (almost always a full-page raster in journal PDFs) and images smaller than e.g. 100 × 100 (logos, form fields).

Both are O(1) per image and remove ≥ 90 % of false-positive furniture matches in our testing.

---

## 5. How to reproduce

```bash
git clone https://github.com/Zensoro/paperdetective.git
cd paperdetective
pip install -e ".[pdf,docx]"

# Download the original article PDF (PLoS "printable" version, 4.3 MB)
curl -L -o examples/her3_brand2013/paper.pdf \
  "https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0071518&type=printable"

# Run the wrapper that filters page rasters + the seven detector pipeline
python examples/her3_brand2013/run.py
# → writes examples/her3_brand2013/report.json and report.md
```

**Reproducibility note:** Benford is the only stochastic component (it relies on a deterministic numeric distribution, so output is stable), and all other detectors are fully deterministic.

---

## 6. Take-away

- The free tier produced **one defensible soft signal** (Benford deviation) — exactly the kind of low-amplitude nudge a research-integrity officer uses to decide whether to look at a paper more closely. It is **not** a verdict.
- The free tier did **not** flag the confirmed fabrication. That is a real gap — and this case study proposes two concrete improvements (region-level pHash + band-level ELA) that would.
- This run uncovered a separate, equally important product bug: printable PDF ingestion returns the shared full-page rasters as figure candidates, flooding pHash with false positives. The recommended fix is two cheap heuristics in `ingest.py`.

Honest tools earn trust. We document both the hits **and** the misses — that is the only way a screening tool is worth shipping.

---

*Generated 2026-08 with PaperDetective `0.3.0`.  
Retraction record: [`10.1371/journal.pone.0267745`](https://doi.org/10.1371/journal.pone.0267745).  
ORI case summary: [`ori.hhs.gov/content/casesummary-brand-toni-m`](https://ori.hhs.gov/content/casesummary-brand-toni-m).*
