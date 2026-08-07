"""Auto-generate a labeled western-blot lane dataset from a PDF corpus.

The deterministic :mod:`paperdetective.detect.lane_reuse` detector is used as a
*high-precision automatic labeler*. Running it over a corpus of papers produces,
for every figure, lane crops labeled into three classes:

* ``duplicate``  — lane participates in a LaneReuse hit (a fabrication signal).
* ``clean_lane`` — lane passes every gate but is not part of any hit (true
  negative for duplication).
* ``rejected``   — lane fails the blot / entropy / height gate. These are the
  false-positive bait for a future segmentation classifier (forest-plot markers,
  flow-chart borders, blank lanes…).

A ``split`` column marks each lane as coming from a ``fraud`` or ``control``
paper, so the control papers can be held out as a test set — exactly the
methodology that proved 0 false positives in v0.6.0.

Two training artifacts are emitted:

* ``images/<class>/<paper>_<fig>_b<band>_l<lane>.png`` — grayscale lane crops,
  height-normalized to a fixed canvas with aspect preserved (padding).
* ``manifest.csv`` — one row per lane with id, class, split, and the scalar
  features the detector already computed (entropy, profile energy, height,
  width, content ratio, best correlation). Enough to train a lightweight
  ``scikit-learn`` classifier without touching pixels.
* ``pairs.csv`` — (laneA, laneB, label) rows: every LaneReuse hit as a positive
  pair, plus a capped sample of same-paper clean↔clean negative pairs. Ready for
  a siamese / contrastive model.
* ``dataset_stats.json`` — class and split counts.

Usage::

    python -m paperdetective.tools.dump_lane_dataset \\
        --corpus /tmp/pd_demo/cases --out data/lanes

``--corpus`` should contain fraud PDFs; a ``clean/`` subdirectory (if present)
holds control papers. Gate parameters default to the module constants but can be
overridden.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from ..detect import lane_reuse as lr
from ..ingest import ingest_path


# Canonical dump canvas (width, height) in pixels. Lanes are tall narrow strips;
# we normalize height and pad width so every crop has a fixed shape.
DUMP_SIZE = (64, 192)
PAD_VALUE = 255  # background (white)


def _dump_crop(band: np.ndarray, x0: int, x1: int, size: tuple[int, int] = DUMP_SIZE) -> Image.Image:
    """Crop one lane, height-normalize with aspect preserved, pad to `size`."""
    tile = np.asarray(band[:, x0:x1], dtype=np.uint8)
    h, w = tile.shape
    th = size[1]
    tw = max(1, int(round(w * th / h)))
    im = Image.fromarray(tile).resize((tw, th), Image.BILINEAR)
    canvas = Image.new("L", size, PAD_VALUE)
    canvas.paste(im, ((size[0] - tw) // 2, 0))
    return canvas


def _lane_content_ratio(band: np.ndarray, x0: int, x1: int) -> float:
    """Fraction of dark (ink) pixels in the lane crop."""
    crop = band[:, x0:x1]
    return float((crop < lr.CONTENT_BG).mean())


def extract_paper(pdf_path: Path, split: str, gates: dict) -> list[dict]:
    """Run segmentation + detectors over one PDF and return per-lane records.

    Each record carries the lane's class, split, geometric/scalar features, and
    (for duplicates) the best correlation. Lanes that fail the gate are kept as
    ``rejected`` so the segmentation classifier has negative examples.
    """
    try:
        doc = ingest_path(str(pdf_path))
    except Exception as exc:  # truncated/corrupt PDF must not kill the batch
        print(f"    ! skip {pdf_path.name}: {type(exc).__name__}: {exc}", file=sys.stderr)
        return [], []
    paper = pdf_path.stem  # DOI with "/" -> "_"
    records: list[dict] = []

    for fig_id, img in doc.images:
        gray = np.asarray(img.convert("L"), dtype=np.float32)
        for bi, (y0, y1) in enumerate(lr.segment_bands(gray)):
            band = gray[y0:y1, :]
            bh = y1 - y0
            lanes = lr.segment_lanes(band)
            is_blot = lr._is_blot_band(band, lanes)
            for li, (x0, x1) in enumerate(lanes):
                prof = lr.lane_profile(band, x0, x1)
                energy = float(prof.mean())
                ent = lr._lane_entropy(band, x0, x1)
                passed = (
                    bh >= gates["min_h"]
                    and is_blot
                    and energy >= gates["min_energy"]
                    and ent >= gates["min_ent"]
                )
                cls = "clean_lane" if passed else "rejected"
                records.append({
                    "paper": paper, "figure": fig_id, "band": bi, "lane": li,
                    "split": split, "class": cls,
                    "x0": x0, "y0": y0, "x1": x1, "y1": y1,
                    "height": int(bh), "width": int(x1 - x0),
                    "entropy": round(ent, 4),
                    "energy": round(energy, 4),
                    "content_ratio": round(_lane_content_ratio(band, x0, x1), 4),
                    "best_corr": "",  # filled after hit detection
                    "crop": _dump_crop(band, x0, x1),
                })

    # Hit detection reuses the public detector (which already applies the gates).
    hits = lr.detect_lane_reuse(dict(doc.images))
    hit_keys = set()
    best_corr: dict[tuple, float] = {}
    hit_pairs: list[tuple[str, str, float]] = []  # (id_a, id_b, corr)
    for h in hits:
        ka = (h["figure_a"], h["band_a"], h["lane_a"])
        kb = (h["figure_b"], h["band_b"], h["lane_b"])
        hit_keys.add(ka)
        hit_keys.add(kb)
        best_corr[ka] = max(best_corr.get(ka, 0.0), h["correlation"])
        best_corr[kb] = max(best_corr.get(kb, 0.0), h["correlation"])
        id_a = _lid(paper, h["figure_a"], h["band_a"], h["lane_a"])
        id_b = _lid(paper, h["figure_b"], h["band_b"], h["lane_b"])
        hit_pairs.append((id_a, id_b, h["correlation"]))
    for r in records:
        k = (r["figure"], r["band"], r["lane"])
        if k in hit_keys:
            r["class"] = "duplicate"
            r["best_corr"] = round(best_corr[k], 4)
    return records, hit_pairs


def _lid(paper: str, fig: str, band: int, lane: int) -> str:
    """Build the same lane id used in the manifest / image filenames."""
    return f"{paper}_{fig}_b{band}_l{lane}"


def _lane_id(r: dict) -> str:
    return f"{r['paper']}_{r['figure']}_b{r['band']}_l{r['lane']}"


def build_pairs(records: list[dict], hit_pairs: list[tuple[str, str, float]],
                 neg_per_pos: int = 3) -> list[dict]:
    """Emit real hit pairs as positives + capped clean↔clean negatives."""
    rng = np.random.default_rng(20260807)
    by_paper_clean: dict[str, list[dict]] = {}
    split_of: dict[str, str] = {}
    paper_of: dict[str, str] = {}
    for r in records:
        if r["class"] == "clean_lane":
            by_paper_clean.setdefault(r["paper"], []).append(r)
        lid = _lane_id(r)
        split_of[lid] = r["split"]
        paper_of[lid] = r["paper"]

    pairs = []
    for id_a, id_b, corr in hit_pairs:
        pairs.append({
            "lane_a": id_a, "lane_b": id_b,
            "label": 1, "corr": round(corr, 4),
            "split": split_of.get(id_a, ""),
        })
    # negative pairs: sample clean lanes from the same paper as each positive
    for id_a, id_b, _ in hit_pairs:
        paper = paper_of.get(id_a)
        pool = by_paper_clean.get(paper, []) if paper else []
        if len(pool) < 2:
            continue
        for other in rng.choice(pool, size=min(neg_per_pos, len(pool)), replace=False):
            pairs.append({
                "lane_a": id_a, "lane_b": _lane_id(other),
                "label": 0, "corr": "",
                "split": split_of.get(id_a, ""),
            })
    return pairs


# ``clean/`` predates the multi-split layout and is kept as an alias so existing
# corpora keep producing the ``control`` split.
SPLIT_ALIASES = {"clean": "control"}


def discover_corpus(corpus: Path) -> list[tuple[Path, str]]:
    """Map every PDF under ``corpus`` to the split it belongs to.

    Top-level PDFs form the ``fraud`` split: papers where an official body
    (ORI, an institutional investigation, a sponsor statement) identified the
    manipulated figures one by one. Every subdirectory becomes its own split, so
    weaker labels never get silently promoted to that gold standard — e.g.
    ``retracted/`` holds papers retracted for image problems where no per-figure
    finding was published, and ``clean/`` holds the negative controls.
    """
    if not corpus.is_dir():
        return []
    items: list[tuple[Path, str]] = []
    for pdf in sorted(corpus.glob("*.pdf")):
        items.append((pdf, "fraud"))
    for sub in sorted(p for p in corpus.iterdir() if p.is_dir()):
        split = SPLIT_ALIASES.get(sub.name, sub.name)
        for pdf in sorted(sub.glob("*.pdf")):
            items.append((pdf, split))
    return items


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", required=True, type=Path,
                    help="Directory of fraud PDFs; each subdirectory is its own "
                         "split (clean/ = control).")
    ap.add_argument("--out", required=True, type=Path, help="Output dataset directory.")
    ap.add_argument("--min-h", type=int, default=lr.LANE_MIN_H)
    ap.add_argument("--min-ent", type=float, default=lr.LANE_MIN_ENTROPY)
    ap.add_argument("--min-energy", type=float, default=lr.PROFILE_MIN_ENERGY)
    ap.add_argument("--no-images", action="store_true", help="Skip PNG crops (labels+features only).")
    args = ap.parse_args(argv)

    gates = {"min_h": args.min_h, "min_ent": args.min_ent, "min_energy": args.min_energy}

    corpus_items = discover_corpus(args.corpus)
    if not corpus_items:
        print(f"no PDFs found in {args.corpus}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    img_root = args.out / "images"
    if not args.no_images:
        for c in ("duplicate", "clean_lane", "rejected"):
            (img_root / c).mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    all_hit_pairs: list[tuple[str, str, float]] = []
    skipped: list[str] = []
    for pdf, split in corpus_items:
        print(f"[{split:9s}] {pdf.name}")
        recs, hp = extract_paper(pdf, split, gates)
        if not recs:
            # Truncated downloads are common and must never be silent: a paper
            # that yields no lanes would otherwise vanish from the stats and
            # quietly deflate the corpus size.
            skipped.append(pdf.name)
        all_records.extend(recs)
        all_hit_pairs.extend(hp)

    # Write crops + manifest
    manifest_path = args.out / "manifest.csv"
    fields = ["id", "paper", "figure", "band", "lane", "split", "class",
              "height", "width", "entropy", "energy", "content_ratio", "best_corr"]
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_records:
            row = {k: r.get(k, "") for k in fields}
            row["id"] = _lane_id(r)
            w.writerow(row)
            if not args.no_images:
                cls_dir = img_root / r["class"]
                r["crop"].save(cls_dir / f"{_lane_id(r)}.png")

    # Write pairs
    pairs = build_pairs(all_records, all_hit_pairs)
    pairs_path = args.out / "pairs.csv"
    with pairs_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["lane_a", "lane_b", "label", "corr", "split"])
        w.writeheader()
        for p in pairs:
            w.writerow(p)

    # Stats
    stats = {"total_lanes": len(all_records), "pairs": len(pairs),
             "papers_in_corpus": len(corpus_items),
             "papers_with_lanes": len(corpus_items) - len(skipped),
             "papers_skipped": sorted(skipped)}
    for key, val in (("class", "class"), ("split", "split")):
        counts: dict[str, int] = {}
        for r in all_records:
            counts[r[val]] = counts.get(r[val], 0) + 1
        stats[f"by_{key}"] = dict(sorted(counts.items()))
    # cross-tab split x class — control must show 0 duplicates
    cross: dict[str, dict[str, int]] = {}
    for r in all_records:
        cross.setdefault(r["split"], {}).setdefault(r["class"], 0)
        cross[r["split"]][r["class"]] += 1
    stats["by_split_class"] = {k: dict(sorted(v.items())) for k, v in sorted(cross.items())}
    (args.out / "dataset_stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote {len(all_records)} lane records to {args.out}")
    print(f"  images : {'(skipped)' if args.no_images else img_root}")
    print(f"  manifest: {manifest_path}")
    print(f"  pairs   : {pairs_path} ({len(pairs)} pairs)")
    print(f"  stats   : {args.out / 'dataset_stats.json'}")
    print("  by class:", stats["by_class"])
    print("  by split:", stats["by_split"])
    if skipped:
        print(f"\n  WARNING: {len(skipped)}/{len(corpus_items)} paper(s) produced no "
              f"lanes — usually a truncated download (a PDF can be the right size "
              f"and still be cut short; check for the %%EOF marker) or a paper with "
              f"no extractable figures:")
        for name in skipped[:12]:
            print(f"    - {name}")
        if len(skipped) > 12:
            print(f"    ... and {len(skipped) - 12} more (see dataset_stats.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
