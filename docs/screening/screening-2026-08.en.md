# Paper-level screening signal evaluation (Screening 2026-08)

> Paper-level screening aggregates lane-level signals (LaneReuse duplication,
> Gabor texture probability, lane count) into **one score per paper**, so that
> editors/reviewers can prioritise which papers deserve closer inspection.
> This document reports the screening-score distribution over 52 known
> retracted papers (positive set) and **232 unseen normal PLOS papers**
> (control pool), as an evidence-level demonstration of the screening ability.

> ⚠️ **Screening signals, not conclusions**: all scores below are statistical
> and image-heuristic screening signals, subject to false positives/negatives;
> a high score ≠ research misconduct, a low score ≠ no anomaly. This document
> does not constitute an accusation, judgement or conclusion about any paper
> or author. Any follow-up must be independently assessed by domain experts
> using the original data, lab records and peer-review process.

## Why paper-level screening

Lane-level classification (see model experiment notes under `docs/`) answers
"does this lane look like a WB band", but editors face **whole papers** — they
need "is this paper worth my time to inspect". Paper-level screening collapses
several independent signals into one sortable score used to **prioritise
inspection**, not to judge.

## Method

Six paper-level features per paper:

| Feature | Meaning | Signal type |
| --- | --- | --- |
| `n_lanes` | auto-segmented lane count | structural |
| `n_dup_pairs` | intra-paper cross-band/cross-figure duplicated lane pairs (same-band adjacent lanes excluded) | hard evidence (pixel) |
| `dup_ratio` | dup pairs / lane count | hard evidence (normalised) |
| `p50_wb` | median WB texture probability of lanes (Gabor+RF, trained on v3 retracted papers) | statistical soft |
| `max_wb` | max single-lane WB texture probability | statistical soft |
| `n_wb_gt_05` | lanes with WB probability > 0.5 | statistical soft |

The 6 features are combined by a random forest (5-fold stratified CV) into a
paper-level screening score (0-1).

## Results

### Screening-score distribution

| Group | n | median | p75 | p90 | p95 | max |
| --- | --- | --- | --- | --- | --- | --- |
| Known retracted papers (positive, v3) | 52 | 0.565 | 0.831 | 0.901 | — | 0.959 |
| Unseen normal papers (control pool, v4) | 232 | 0.281 | 0.368 | 0.484 | 0.586 | 0.929 |

### Threshold behaviour (232-paper control pool)

| Threshold | Papers flagged high-signal | Ratio |
| --- | --- | --- |
| > 0.8 | 3 | 1.3% |
| > 0.7 | 5 | 2.2% |
| > 0.6 | 11 | 4.7% |

Using 0.8 as a "priority review" threshold, **only 1.3% of the 232 normal
papers would be flagged** — the screening tool does not drown the normal pool
in false alarms.

## Honest boundaries

1. **Optimistic positives**: v3 retracted papers are scored by a model trained
   ON v3, so the positive-side distribution above is an **upper bound**; the
   control-pool distribution (truly unseen papers) is the unbiased reading.
2. **Control pool not manually verified**: "normal" only means not in our case
   library and without an official retraction flag — **it does not imply the
   content is anomaly-free**. The highest-scoring control papers were also hit
   by an independent pixel-duplication line, making them "worth manual
   inspection" candidates — consistent with screening's role:
   **screening finds leads, it does not close cases**. No specific papers are
   listed in this document to avoid any implied association.
3. **Genre bias**: all 232 control papers are PLOS; cross-journal
   generalisation of paper-level screening needs larger validation.
4. **Thresholds not tuned**: 0.8/0.7/0.6 are illustrative, not tuned;
   they only show the shape of the distribution.

## Relation to single detectors
| `10.1371/journal.pone.0017407` | 0.723 | 0 | 15 | 0.81 | — |
| `10.1371/journal.pone.0319316` | 0.723 | 2 | 49 | 0.80 | — |

## Relation to single detectors

- LaneReuse lane-level duplication (hard evidence) remains the strongest
  single signal;
- the value of paper-level screening is **aggregation**: compressing several
  soft signals plus hard evidence into one sortable score so editors can
  prioritise review across many papers;
- a screening score never replaces the evidence detail of any single detector —
  reviewers should return to the concrete evidence locations (page/figure/lane).

## Reproduction

> ⚠️ The screening corpus behind this document (paper PDFs, lane crops,
> labels) is **not shipped with the repository** — it was collected
> experimentally by the author, subject to copyright/compliance
> considerations; the screening tool script is likewise not shipped because
> it depends on that corpus. To reproduce, you need a structurally similar
> corpus (lane extractions from retracted + normal papers) and an
> implementation of the paper-level feature aggregation (6 features defined
> in the Method section; random forest with 5-fold stratified CV).

Output format (`screening.json`): per-paper 6 features + 5-fold OOF scores.
