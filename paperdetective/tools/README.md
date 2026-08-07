# Developer tools

Standalone utilities for building, evaluating, and experimenting with
PaperDetective. These are **not** part of the detection pipeline — they exist to
support the corpus-driven development methodology (see
`docs/case-studies/corpus-2026-08.md`).

## `dump_lane_dataset.py` — auto-generate a labeled lane dataset

The deterministic `LaneReuse` detector is used as a **high-precision automatic
labeler**: run it over a corpus of PDFs and every western-blot lane is cropped
and labeled. This is the foundation for any future neural classifier (the
project deliberately does *not* train on 8 papers today — see the overfitting
discussion — but the data has to be collected first).

### Usage

```bash
python -m paperdetective.tools.dump_lane_dataset \
    --corpus /path/to/cases \     # top-level PDFs = fraud; each subdir = its own split
    --out    data/lanes
```

#### Corpus layout and label strength

Every subdirectory of `--corpus` becomes its own `split`, which is how labels of
different strength are kept apart. **Never flatten these into one split** — they
are not equally trustworthy:

```
cases/
  *.pdf            -> split=fraud      gold standard: an official body (ORI, an
                                       institutional investigation, a sponsor
                                       statement) named the manipulated figures
  retracted/*.pdf  -> split=retracted  weak label: retracted for image problems,
                                       but no per-figure finding was published
  clean/*.pdf      -> split=control    negative control: must never produce a
                                       duplicate (clean/ is aliased to control
                                       for backwards compatibility)
```

`fraud` is the only split where a `duplicate` label can be checked against a
published finding. `retracted` papers are *likely* to contain reuse, but the
detector's output there is unverified — useful as training volume, never as
ground truth for measuring precision.

Gate parameters default to the `lane_reuse` module constants
(`--min-h`, `--min-ent`, `--min-energy`); `--no-images` skips PNG crops and emits
labels + features only.

### Output schema

```
data/lanes/
  images/
    duplicate/  <paper>_<fig>_b<band>_l<lane>.png   # lane in a LaneReuse hit
    clean_lane/ ...                                 # passed gates, not a hit
    rejected/   ...                                 # failed the blot/entropy gate
  manifest.csv      # one row per lane, with scalar features
  pairs.csv         # (lane_a, lane_b, label) for siamese training
  dataset_stats.json
```

**`manifest.csv` columns**

| column | meaning |
| --- | --- |
| `id` | `<paper>_<fig>_b<band>_l<lane>` (matches the PNG filename) |
| `paper`, `figure`, `band`, `lane` | source location |
| `split` | `fraud` / `retracted` / `control` (or any subdir name) — hold `control` out as a test set; see label strength above |
| `class` | `duplicate` / `clean_lane` / `rejected` |
| `height`, `width` | lane geometry (px) |
| `entropy` | 32-bin gray histogram entropy of the lane |
| `energy` | mean of the normalized intensity profile |
| `content_ratio` | fraction of ink pixels |
| `best_corr` | strongest correlation for duplicate lanes (else blank) |

**`pairs.csv`** has one row per (lane_a, lane_b) pair: every LaneReuse hit as a
`label=1` pair of *two distinct* lanes, plus a capped sample of same-paper
`clean_lane`↔`clean_lane` `label=0` pairs. Ready for a siamese / contrastive
model without any further pairing logic.

### Two training targets this dataset supports

1. **Blot segmentation classifier** (replaces the hand-tuned gates in ①).
   Train `is_real_blot_lane` on `{duplicate, clean_lane}` (positive) vs
   `rejected` (negative), using either the PNG crops (CNN) or the `manifest.csv`
   scalar features (`scikit-learn`). The `rejected` class is the false-positive
   bait the gates were tuned against.
2. **Duplicate detector** (②). Train a siamese/contrastive model on `pairs.csv`,
   or a plain classifier on `duplicate` vs `clean_lane` crops.

### Validation methodology (do not break this)

`dataset_stats.json` carries a `by_split_class` cross-tab. The control papers
must show **zero duplicates** — that is the empirical proof the auto-labeler has
no false positives on papers it was never tuned on. If a future change makes
`control.duplicate > 0`, the gates regressed; investigate before shipping.

> The dataset itself (thousands of PNGs) is git-ignored — only this tool and its
> tests are committed. Reproduce it with the command above against the corpus
> PDFs (DOIs listed in `docs/case-studies/corpus-2026-08.md`).
