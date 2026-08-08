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
        "# 🔍 PaperDetective 筛查报告",
        "",
        "> 本报告为**自动化筛查信号**，供领域专家人工复核使用；不构成学术不端判定。",
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
            "## ✅ 筛查结果：未发现显著异常信号",
            "",
        ]
        if result.internal_review.no_findings_reason:
            lines.append(f"> {result.internal_review.no_findings_reason}")
            lines.append("")
    else:
        lines += [
            f"## ⚠️ 筛查结果：发现 **{n}** 项需人工复核的信号",
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
        "",
        "> ⚠️ **方法局限**：GRIM/SPRITE/Benford/p-curve/ELA 等均为统计或",
        "> 图像启发式，存在误报与漏报；统计异常不等于学术不端。",
        ">",
        "> ⚠️ **非鉴定结论**：本报告仅描述检测到的异常信号及其证据位置，",
        "> 不构成对论文或作者的任何指控、评判或结论，不具备鉴定效力。",
        ">",
        "> ⚠️ **复核要求**：任何后续处理须由领域专家结合原始数据、实验记录",
        "> 与同行评议流程独立判断，本工具不替代上述流程。",
        ">",
        "> ⚠️ **数据来源**：分析仅基于所提供的论文文本/图片，作者未核实其",
        "> 获取渠道之合法性，用户须确保数据来源合规并遵守相关版权要求。",
    ]
    if result.internal_review.missing_info:
        lines.append(f">")
        lines.append(f"> ℹ️ {result.internal_review.missing_info}")
    return "\n".join(lines) + "\n"
