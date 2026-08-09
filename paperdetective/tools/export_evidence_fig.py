"""Export evidence figures for LaneReuse findings from a PaperDetective report.

Reads a PaperDetective JSON report (analyze --output *.json), finds LaneReuse
findings with pixel-box evidence (extra.box_a / extra.box_b), loads the two
source figures from a local images dir, and writes a side-by-side annotated
montage per finding.

Zero new dependencies: uses only Pillow + stdlib.

Usage:
    python -m paperdetective.tools.export_evidence_fig \
        --report report.json --images-dir ./figures --out ./evidence
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw


def _crop_box(img: Image.Image, box: list[int]) -> Image.Image:
    """box = [x0, y0, x1, y1]; clamp to image bounds."""
    w, h = img.size
    x0, y0, x1, y1 = box
    x0 = max(0, min(x0, w)); x1 = max(x0, min(x1, w))
    y0 = max(0, min(y0, h)); y1 = max(y0, min(y1, h))
    return img.crop((x0, y0, x1, y1))


def _resolve(path: str) -> str | None:
    if os.path.exists(path):
        return path
    for ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
        cand = path + ext
        if os.path.exists(cand):
            return cand
    return None


def export(report_path: str, images_dir: str, out_dir: str, pad: int = 10,
           strip_h: int = 160) -> list[str]:
    report = json.load(open(report_path, encoding="utf-8"))
    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    n = 0
    for finding in report.get("detected_findings", []):
        if finding.get("detection_method") != "LaneReuse":
            continue
        for ev in finding.get("evidence_pack", []):
            extra = ev.get("extra") or {}
            fa, fb = extra.get("figure_a"), extra.get("figure_b")
            box_a, box_b = extra.get("box_a"), extra.get("box_b")
            if not (fa and fb and box_a and box_b):
                continue
            pa = _resolve(os.path.join(images_dir, os.path.basename(fa)))
            pb = _resolve(os.path.join(images_dir, os.path.basename(fb)))
            if not (pa and pb):
                continue
            ima = Image.open(pa).convert("RGB")
            imb = Image.open(pb).convert("RGB")
            crop_a = _crop_box(ima, box_a)
            crop_b = _crop_box(imb, box_b)
            h = max(crop_a.size[1], crop_b.size[1], strip_h)
            strip = Image.new("RGB", (crop_a.size[0] + crop_b.size[0] + 3 * pad, h + 2 * pad), "white")
            strip.paste(crop_a, (pad, pad))
            strip.paste(crop_b, (pad + crop_a.size[0] + pad, pad))
            d = ImageDraw.Draw(strip)
            d.text((pad, 2), f"{fa}", fill=(200, 0, 0))
            d.text((pad + crop_a.size[0] + pad, 2), f"{fb}", fill=(200, 0, 0))
            out = os.path.join(out_dir, f"lane_dup_{n:03d}.png")
            strip.save(out)
            written.append(out)
            n += 1
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", required=True, help="PaperDetective JSON report")
    ap.add_argument("--images-dir", required=True, help="dir containing figure images")
    ap.add_argument("--out", default="evidence", help="output dir for montages")
    args = ap.parse_args(argv)
    written = export(args.report, args.images_dir, args.out)
    print(f"exported {len(written)} evidence figure(s) to {args.out}")
    for p in written:
        print(f"  {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
