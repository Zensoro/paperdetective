"""Command-line interface for PaperDetective.

Subcommands:
  analyze   Run the full detection pipeline on one or more files/dirs.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .ingest import ingest_path
from .analyze import run_detection
from .report import to_markdown

SUPPORTED_SUFFIXES = {".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".gif", ".bmp"}

_SEVERITY_ICON = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}


def _use_color() -> bool:
    return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _use_color() else text


def _expand_inputs(inputs: list[str]) -> tuple[list[Path], list[str]]:
    """Expand files/dirs into a sorted list of supported files; collect warnings."""
    files: list[Path] = []
    warnings: list[str] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            found = sorted(f for f in p.rglob("*")
                           if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES)
            if not found:
                warnings.append(f"目录 {p} 中未找到可支持的文件")
            files.extend(found)
        elif p.is_file():
            files.append(p)
        else:
            warnings.append(f"输入不存在，已跳过: {p}")
    return files, warnings


def _print_summary(result, skipped: list[str]) -> None:
    n = len(result.detected_findings)
    print()
    print(_c("┌─ PaperDetective 检测摘要 " + "─" * 34, "1"))
    print(f"│ 论文数: {len(result.analysis_metadata['papers'])}"
          f"   模式: {result.analysis_metadata['mode']}"
          f"   检测器: {', '.join(result.analysis_metadata.get('detectors_run', [])) or '-'}")
    if n == 0:
        print(f"│ {_c('✅ 未发现六类造假信号', '32')}")
    else:
        print(f"│ 发现 {_c(str(n), '1;31')} 项问题:")
        for f in result.detected_findings:
            icon = _SEVERITY_ICON.get(f.severity, "⚪")
            print(f"│   {icon} [{f.severity:<6}] {f.title} ({f.detection_method}, 置信度 {f.confidence_score:.2f})")
    for s in skipped:
        print(f"│ {_c('⚠️  ' + s, '33')}")
    print(_c("└" + "─" * 58, "1"))
    print()


def _cmd_analyze(args) -> int:
    files, warnings = _expand_inputs([str(p) for p in args.input])
    if not files:
        for w in warnings:
            print(f"warning: {w}", file=sys.stderr)
        print("error: 没有可分析的文件", file=sys.stderr)
        return 2

    docs = []
    skipped = list(warnings)
    for f in files:
        try:
            docs.append(ingest_path(str(f)))
        except Exception as e:  # 单个文件失败不应拖垮整批
            skipped.append(f"{f.name}: {e}")

    if not docs:
        for s in skipped:
            print(f"warning: {s}", file=sys.stderr)
        print("error: 所有输入文件均解析失败", file=sys.stderr)
        return 2

    result = run_detection(docs, pro=args.pro, license_key=args.license)
    if args.markdown:
        out = args.output or "paperdetective_report.md"
        Path(out).write_text(to_markdown(result), encoding="utf-8")
    else:
        out = args.output or "paperdetective_report.json"
        Path(out).write_text(result.model_dump_json(indent=2), encoding="utf-8")
    _print_summary(result, skipped)
    print(f"报告已写入: {out}", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="paperdetective",
                                     description="PaperDetective 学术打假检测器")
    parser.add_argument("--version", action="version",
                        version=f"paperdetective {__version__}")
    sub = parser.add_subparsers(dest="cmd")
    pa = sub.add_parser("analyze", help="run detection pipeline")
    pa.add_argument("--input", nargs="+", required=True,
                    help="input files or directories (txt/pdf/docx/images)")
    pa.add_argument("--output", help="output file path")
    pa.add_argument("--markdown", action="store_true",
                    help="emit Markdown instead of JSON")
    pa.add_argument("--pro", action="store_true",
                    help="enable PRO-tier network detectors (DOI existence check)")
    pa.add_argument("--license", help="PRO license key (paperdetective-pro)")
    args = parser.parse_args(argv)
    if args.cmd == "analyze":
        return _cmd_analyze(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
