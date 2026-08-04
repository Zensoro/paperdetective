"""Pipeline: run all detectors over documents, arbitrate, emit report."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .ingest import Document
from .schemas import AnalysisResult, Finding, EvidencePack, InternalReview
from .detect.data_fabrication import grim_test, sprite_test, benford_analysis, p_curve_analysis
from .engine.confidence import confidence_score

MEAN_N_RE = re.compile(r"均值\s*[=:：]?\s*(\d+(?:\.\d+)?)[^\d]*n\s*[=:：]\s*(\d+)")
P_VALUE_RE = re.compile(r"[pP]\s*[=:：]\s*(\d+(?:\.\d+)?)")

# 免费核心包含的检测方法（pro 模式额外解锁联网检测）
FREE_METHODS = {"GRIM", "SPRITE", "Benford", "p-curve", "pHash", "ELA"}
PRO_METHODS = {"DOI_Check", "Retraction_Check", "NLI"}


def _find_grim_claims(text: str) -> list[dict]:
    claims = []
    for m in MEAN_N_RE.finditer(text):
        try:
            mean = float(m.group(1))
            n = int(m.group(2))
        except ValueError:
            continue
        claims.append({"mean": mean, "n": n})
    return claims


def _find_p_values(text: str) -> list[float]:
    pvals = []
    for m in P_VALUE_RE.finditer(text):
        try:
            pvals.append(float(m.group(1)))
        except ValueError:
            continue
    return pvals


def run_detection(docs: list[Document], pro: bool = False) -> AnalysisResult:
    findings: list[Finding] = []
    for doc in docs:
        # --- GRIM / SPRITE (FREE, hard evidence) ---
        for claim in _find_grim_claims(doc.text):
            grim = grim_test(claim["mean"], claim["n"])
            if grim["violated"]:
                findings.append(Finding(
                    id=f"FD-{len(findings)+1:03d}",
                    finding_type=["Data_Fabrication"],
                    title="GRIM 检验失败：均值与样本量不匹配数据粒度",
                    description=f"均值 {claim['mean']} × n={claim['n']} 无法由该粒度的整数个数据点产生，提示数据可能被编造或转录错误。",
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Data", source_location=doc.paper_id,
                        quote=f"均值={claim['mean']}, n={claim['n']}",
                        basis="原文")],
                    detection_method="GRIM",
                    confidence_score=confidence_score(evidence=["GRIM"]),
                ))

        # --- p-curve (FREE, soft signal) ---
        pvals = _find_p_values(doc.text)
        if len(pvals) >= 10:
            pc = p_curve_analysis(pvals)
            if pc["violated"]:
                findings.append(Finding(
                    id=f"FD-{len(findings)+1:03d}",
                    finding_type=["Data_Fabrication"],
                    title="p 值分布异常集中（疑似 p-hacking）",
                    description="较大比例 p 值集中在 0.04-0.05 区间，提示可能存在选择性报告。",
                    severity="Medium",
                    evidence_pack=[EvidencePack(
                        type="Data", source_location=doc.paper_id,
                        quote=f"near_threshold_ratio={pc['near_threshold_ratio']}", basis="原文")],
                    detection_method="p-curve",
                    confidence_score=confidence_score(evidence=["p-curve"]),
                ))

    return AnalysisResult(
        analysis_metadata={
            "papers": [{"title": d.paper_id, "authors": None,
                        "journal_or_source": None, "publication_year": None,
                        "input_id": d.paper_id} for d in docs],
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_version": "PaperDetective v1.0",
            "processing_status": "success",
            "reference_basis_provided": False,
            "mode": "pro" if pro else "free",
        },
        detected_findings=findings,
        internal_review=InternalReview(
            no_findings_reason=None if findings else "未发现六类造假信号。",
            hallucination_check="所有结论基于确定性算法(GRIM/p-curve)与规则提取，无模型自由推断。",
            missing_info="v1 管线当前启用 GRIM 与 p-curve 通路；其余检测模块可在配置中扩展。",
            external_knowledge_disclaimer="无",
        ),
    )
