"""Report generation: JSON (native) + Markdown export."""
from __future__ import annotations

from .schemas import AnalysisResult

_SEVERITY_ICON = {"High": "🔴 高", "Medium": "🟡 中", "Low": "🟢 低"}
_SEVERITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}


def to_markdown(result: AnalysisResult) -> str:
    meta = result.analysis_metadata
    findings = sorted(result.detected_findings,
                      key=lambda f: (_SEVERITY_ORDER.get(f.severity, 3), f.id))
    n = len(findings)
    n_high = sum(1 for f in findings if f.severity == "High")
    n_med = sum(1 for f in findings if f.severity == "Medium")
    n_low = n - n_high - n_med

    lines = [
        "# 🔍 PaperDetective 检测报告",
        "",
        "| 项目 | 内容 |",
        "| --- | --- |",
        f"| 引擎 | {meta.get('agent_version', '-')} |",
        f"| 分析时间 | {meta.get('analysis_timestamp', '-')} |",
        f"| 运行模式 | {'💎 PRO' if meta.get('mode') == 'pro' else '🆓 Free'} |",
        f"| 状态 | {meta.get('processing_status', '-')} |",
        f"| 检测器 | {', '.join(meta.get('detectors_run', [])) or '-'} |",
        f"| 论文 | {', '.join(str(p.get('title')) for p in meta.get('papers', [])) or '-'} |",
        "",
        "---",
        "",
    ]

    if n == 0:
        lines += [
            "## ✅ 结论：未发现六类造假信号",
            "",
        ]
        if result.internal_review.no_findings_reason:
            lines.append(f"> {result.internal_review.no_findings_reason}")
            lines.append("")
    else:
        lines += [
            f"## ⚠️ 结论：发现 **{n}** 项可疑信号",
            "",
            "| 🔴 高 | 🟡 中 | 🟢 低 |",
            "| :---: | :---: | :---: |",
            f"| {n_high} | {n_med} | {n_low} |",
            "",
            "---",
            "",
            "## 发现明细",
        ]
        for f in findings:
            icon = _SEVERITY_ICON.get(f.severity, f.severity)
            lines += [
                "",
                f"### {icon} `{f.id}` {f.title}",
                "",
                f"- **类型**：{', '.join(f.finding_type)}",
                f"- **检测方法**：{f.detection_method}",
                f"- **置信度**：{f.confidence_score:.2f}",
                f"- **说明**：{f.description}",
            ]
            if f.evidence_pack:
                lines.append("- **证据**：")
                for e in f.evidence_pack:
                    lines.append("")
                    lines.append(f"  > 📍 `{e.source_location}`（{e.type}）")
                    lines.append(f"  > {e.quote}")
            lines.append("")

    lines += [
        "---",
        "",
        f"> ⚖️ **免责声明**：{result.internal_review.disclaimer}",
    ]
    if result.internal_review.missing_info:
        lines.append(f">")
        lines.append(f"> ℹ️ {result.internal_review.missing_info}")
    return "\n".join(lines) + "\n"
