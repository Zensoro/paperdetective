"""Report generation: JSON (native) + Markdown export."""
from __future__ import annotations

from .schemas import AnalysisResult


def to_markdown(result: AnalysisResult) -> str:
    lines = ["# PaperDetective 检测报告", ""]
    meta = result.analysis_metadata
    lines.append(f"- Agent: {meta.get('agent_version')}")
    lines.append(f"- 状态: {meta.get('processing_status')}")
    lines.append(f"- 论文: {[p.get('title') for p in meta.get('papers', [])]}")
    lines.append("")
    if not result.detected_findings:
        lines.append("## 结论：未发现六类造假信号")
        if result.internal_review.no_findings_reason:
            lines.append(f"> {result.internal_review.no_findings_reason}")
        lines.append("")
        lines.append(f"> 免责声明：{result.internal_review.disclaimer}")
        return "\n".join(lines)
    lines.append(f"## 发现 {len(result.detected_findings)} 项问题")
    for f in result.detected_findings:
        lines.append("")
        lines.append(f"### {f.id}: {f.title} ({f.severity})")
        lines.append(f"- 类型: {', '.join(f.finding_type)}")
        lines.append(f"- 检测方法: {f.detection_method}")
        lines.append(f"- 置信度: {f.confidence_score:.2f}")
        lines.append(f"- 描述: {f.description}")
        for e in f.evidence_pack:
            lines.append(f"  - 证据({e.type}): {e.source_location} | {e.quote}")
    lines.append("")
    lines.append(f"> 免责声明：{result.internal_review.disclaimer}")
    return "\n".join(lines)
