"""Pipeline: run all detectors over documents, arbitrate, emit report."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .ingest import Document
from .schemas import AnalysisResult, Finding, EvidencePack, InternalReview
from .detect.data_fabrication import grim_test, benford_analysis, p_curve_analysis
from .detect.image_manipulation import ela_score, detect_reuse
from .detect.internal_inconsistency import extract_numbers
from .detect.cross_paper import find_cross_paper_duplicates
from .plugins import load_pro_extensions, ProContext
from .engine.confidence import confidence_score

# 中英文均值声明: "均值=12.3, n=40" / "mean = 1.33, n = 30" / "M=2.66 (n=12)"
MEAN_N_RE = re.compile(
    r"(?:均值|\bmean\b|\bM\b)\s*[=:：]?\s*(\d+(?:\.\d+)?)"
    r".{0,30}?\b[nN]\b[^\d\n]{0,5}(\d+)",
    re.IGNORECASE,
)
P_VALUE_RE = re.compile(r"[pP]\s*[=:：]\s*(\d*\.\d+|\d+)")

# Benford 分布检验在小样本上噪声极大，设置最小样本量避免误报
BENFORD_MIN_SAMPLE = 20
# p-curve 需要足够数量的精确 p 值才有统计意义
P_CURVE_MIN_SAMPLE = 10

# 免费核心包含的检测方法（pro 能力由 paperdetective-pro 扩展提供）
FREE_METHODS = {"GRIM", "SPRITE", "Benford", "p-curve", "pHash", "ELA"}


def _find_grim_claims(text: str) -> list[dict]:
    claims = []
    for m in MEAN_N_RE.finditer(text):
        try:
            claims.append({"mean": float(m.group(1)), "n": int(m.group(2))})
        except ValueError:
            continue
    return claims


def _find_p_values(text: str) -> list[float]:
    pvals = []
    for m in P_VALUE_RE.finditer(text):
        try:
            pvals.append(float(m.group(1)))
        except ValueError:
            continue
    return pvals


def _mk_finding(findings: list[Finding], **kwargs) -> None:
    findings.append(Finding(id=f"FD-{len(findings)+1:03d}", **kwargs))


def run_detection(docs: list[Document], pro: bool = False, license_key: str | None = None) -> AnalysisResult:
    findings: list[Finding] = []
    detectors_run: list[str] = []

    for doc in docs:
        # --- GRIM (FREE, hard evidence) ---
        for claim in _find_grim_claims(doc.text):
            grim = grim_test(claim["mean"], claim["n"])
            if grim["violated"]:
                _mk_finding(
                    findings,
                    finding_type=["Data_Fabrication"],
                    title="GRIM 检验失败：均值与样本量在整数数据下不可能成立",
                    description=(
                        f"报告均值 {claim['mean']}、n={claim['n']}：最接近的整数总分 "
                        f"{grim['nearest_integer_total']} 反推均值为 {grim['reconstructed_mean']}，"
                        "与报告值不符，提示数据可能被编造或转录错误。"
                    ),
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Data", source_location=doc.paper_id,
                        quote=f"均值={claim['mean']}, n={claim['n']}",
                        basis="原文")],
                    detection_method="GRIM",
                    confidence_score=confidence_score(evidence=["GRIM"]),
                )
        detectors_run.append("GRIM")

        # --- p-curve (FREE, soft signal) ---
        pvals = _find_p_values(doc.text)
        if len(pvals) >= P_CURVE_MIN_SAMPLE:
            pc = p_curve_analysis(pvals)
            detectors_run.append("p-curve")
            if pc["violated"]:
                _mk_finding(
                    findings,
                    finding_type=["Data_Fabrication"],
                    title="p 值分布异常集中（疑似 p-hacking）",
                    description="较大比例 p 值集中在 0.04-0.05 区间，提示可能存在选择性报告。",
                    severity="Medium",
                    evidence_pack=[EvidencePack(
                        type="Data", source_location=doc.paper_id,
                        quote=f"near_threshold_ratio={pc['near_threshold_ratio']}",
                        basis="原文")],
                    detection_method="p-curve",
                    confidence_score=confidence_score(evidence=["p-curve"]),
                )

        # --- Benford (FREE, soft signal, 需要足够样本) ---
        numbers = extract_numbers(doc.text)
        if len(numbers) >= BENFORD_MIN_SAMPLE:
            bf = benford_analysis(numbers)
            detectors_run.append("Benford")
            if bf["violated"]:
                _mk_finding(
                    findings,
                    finding_type=["Data_Fabrication"],
                    title="数字首位分布偏离 Benford 定律",
                    description=(
                        f"文本中 {bf['n']} 个数字的首位分布与 Benford 期望的最大偏差 "
                        f"{bf['deviation']:.3f}（首位 1 占比 {bf['digit1_pct']:.1%}，期望约 30.1%），"
                        "提示数字可能经人工编造。"
                    ),
                    severity="Low",
                    evidence_pack=[EvidencePack(
                        type="Data", source_location=doc.paper_id,
                        quote=f"n={bf['n']}, deviation={bf['deviation']}",
                        basis="原文")],
                    detection_method="Benford",
                    confidence_score=confidence_score(evidence=["Benford"]),
                )

        # --- 文内图片复用 pHash (FREE, hard evidence) ---
        if len(doc.images) >= 2:
            detectors_run.append("pHash")
            for a, b in detect_reuse(dict(doc.images)):
                _mk_finding(
                    findings,
                    finding_type=["Image_Manipulation"],
                    title="文内图片高度相似（疑似复用/拼接）",
                    description=f"图片 {a} 与 {b} 的感知哈希几乎一致，提示同一张图可能被重复用于不同结果。",
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Visual", source_location=doc.paper_id,
                        quote=f"{a} ≈ {b}", basis="原文")],
                    detection_method="pHash",
                    confidence_score=confidence_score(evidence=["pHash"]),
                )

        # --- ELA (FREE, soft signal) ---
        if doc.images:
            detectors_run.append("ELA")
            for img_id, img in doc.images:
                ela = ela_score(img)
                if ela["violated"]:
                    _mk_finding(
                        findings,
                        finding_type=["Image_Manipulation"],
                        title="图片错误水平分析（ELA）异常",
                        description=(
                            f"图片 {img_id} 重压缩误差均值 {ela['ela_score']:.2f}，且误差空间集中"
                            f"（峰值块均值 {ela['max_block_mean']:.2f}，为全局 {ela['block_contrast']:.1f} 倍），"
                            "提示局部区域可能被编辑。"
                        ),
                        severity="Medium",
                        evidence_pack=[EvidencePack(
                            type="Visual", source_location=doc.paper_id,
                            quote=f"ela_score={ela['ela_score']}", basis="原文")],
                        detection_method="ELA",
                        confidence_score=confidence_score(evidence=["ELA"]),
                    )

        # --- PRO 扩展（联网检测，仅当安装 paperdetective-pro 时启用）---
        if pro:
            for run_pro in load_pro_extensions():
                ctx = ProContext(start_id=len(findings) + 1, license_key=license_key)
                run_pro(doc, ctx)
                findings.extend(ctx.findings)
                detectors_run.extend(ctx.detectors_run)

    # --- 跨论文图片复用 (FREE, 多篇输入时启用) ---
    if len(docs) >= 2:
        papers = {d.paper_id: {"images": dict(d.images)} for d in docs}
        cross = find_cross_paper_duplicates(papers)
        if cross:
            detectors_run.append("CrossCheck")
        for a, b, _kind in cross:
            _mk_finding(
                findings,
                finding_type=["Cross_Paper_Duplication"],
                title="跨论文图片复用",
                description=f"图片 {a} 与 {b} 来自不同论文但感知哈希几乎一致，提示一图多用。",
                severity="High",
                evidence_pack=[EvidencePack(
                    type="Visual", source_location=f"{a} | {b}",
                    quote=f"{a} ≈ {b}", basis="原文")],
                detection_method="pHash",
                confidence_score=confidence_score(evidence=["pHash"]),
            )

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
            "detectors_run": sorted(set(detectors_run)),
        },
        detected_findings=findings,
        internal_review=InternalReview(
            no_findings_reason=None if findings else "未发现六类造假信号。",
            hallucination_check="所有结论基于确定性算法(GRIM/Benford/p-curve/pHash/ELA)与规则提取，无模型自由推断。",
            missing_info=(
                "联网检测（DOI/撤稿核查）、NLI、批量扫描、PDF 报告为 Pro 扩展（paperdetective-pro），"
                "当前未安装；"
            ) + "PDF 内嵌图片提取将在后续版本接入。",
            external_knowledge_disclaimer="PRO 扩展的联网检测依赖外部公开服务（如 doi.org）。"
            if pro else "无",
        ),
    )
