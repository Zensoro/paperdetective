"""Command-line interface for PaperDetective.

Subcommands:
  analyze   Run the full detection pipeline on one or more files/dirs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ingest import ingest_path
from .analyze import run_detection
from .report import to_markdown


def _cmd_analyze(args, _) -> int:
    inputs = [str(p) for p in args.input]
    docs = [ingest_path(p) for p in inputs]
    result = run_detection(docs, pro=args.pro)
    if args.markdown:
        out = args.output or "paperdetective_report.md"
        Path(out).write_text(to_markdown(result), encoding="utf-8")
    else:
        out = args.output or "paperdetective_report.json"
        Path(out).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    print(f"report written to {out}", file=sys.stderr)
    print(f"findings: {len(result.detected_findings)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperdetective",
                                     description="PaperDetective 学术打假检测器")
    parser.add_argument("--version", action="version",
                        version=f"paperdetective {__version__}")
    sub = parser.add_subparsers(dest="cmd")
    pa = sub.add_parser("analyze", help="run detection pipeline")
    pa.add_argument("--input", nargs="+", required=True,
                    help="input files or directories")
    pa.add_argument("--output", help="output file path")
    pa.add_argument("--markdown", action="store_true",
                    help="emit Markdown instead of JSON")
    pa.add_argument("--pro", action="store_true",
                    help="enable PRO-tier network detectors (paid)")
    args = parser.parse_args(argv)
    if args.cmd == "analyze":
        return _cmd_analyze(args, None)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
