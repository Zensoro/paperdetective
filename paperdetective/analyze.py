"""Pipeline: run all detectors over documents, arbitrate, emit report."""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .ingest import Document
from .schemas import AnalysisResult, Finding, EvidencePack, InternalReview
from .detect.data_fabrication import grim_test, benford_analysis, p_curve_analysis
from .detect.citation_fraud import check_doi_existence, scan_retraction_keywords, find_dois
from .detect.image_manipulation import ela_score, detect_reuse
from .detect.region_reuse import detect_panel_reuse
from .detect.band_ela import band_ela_scan
from .detect.lane_reuse import cluster_lane_hits, detect_lane_reuse
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
FREE_METHODS = {"GRIM", "SPRITE", "Benford", "p-curve", "pHash", "ELA", "RegionReuse", "BandELA", "LaneReuse"}


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


def run_detection(
    docs: list[Document],
    pro: bool = False,
    license_key: str | None = None,
    _get=None,
) -> AnalysisResult:
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

        # --- DOI 核查 (FREE, 联网尽力而为) ---
        # 检查引文 DOI 是否真实存在。联网失败时降级为 None（不可验证），
        # 不武断下结论；见 detect/citation_fraud.py。
        if _get is not None or True:  # always run; network-safe by design
            for doi in find_dois(doc.text):
                exists = check_doi_existence(doi, _get=_get)
                detectors_run.append("DOI_Check")
                if exists is False:
                    _mk_finding(
                        findings,
                        finding_type=["Citation_Fabrication"],
                        title="引文 DOI 无法解析（疑似虚构引用）",
                        description=(
                            f"DOI {doi} 格式合法但在 doi.org 上解析失败，"
                            "提示该引用可能不存在（也可能是 DOI 登记延迟或"
                            "网络问题，需人工复核）。"
                        ),
                        severity="High",
                        evidence_pack=[EvidencePack(
                            type="Text", source_location=doc.paper_id,
                            quote=doi, basis="原文")],
                        detection_method="DOI_Check",
                        confidence_score=confidence_score(evidence=["DOI_Check"]),
                    )
            # 撤稿关键词扫描（对论文元信息，无联网）
            retraction_words = scan_retraction_keywords(
                {"title": doc.paper_id, "type": ""})
            if retraction_words:
                detectors_run.append("Retraction_Check")
                _mk_finding(
                    findings,
                    finding_type=["Retraction_Flag"],
                    title="论文标题含撤稿/更正标记",
                    description=(
                        f"标题中出现撤稿相关关键词：{', '.join(retraction_words)}。"
                        "可能已被撤稿或发布更正，需人工核实。"
                    ),
                    severity="Medium",
                    evidence_pack=[EvidencePack(
                        type="Text", source_location=doc.paper_id,
                        quote=doc.paper_id, basis="原文")],
                    detection_method="Retraction_Check",
                    confidence_score=confidence_score(evidence=["Retraction_Check"]),
                )

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

        # --- 面板级复用 RegionReuse (FREE, hard evidence) ---
        # 整图 pHash 看不到子图/面板级复用（如 western blot 面板被复制/挪动）。
        # 将每张图按空白投影切成面板后分别哈希，跨图/跨面板比对。
        if doc.images:
            detectors_run.append("RegionReuse")
            for hit in detect_panel_reuse(dict(doc.images)):
                _mk_finding(
                    findings,
                    finding_type=["Image_Manipulation"],
                    title="子图面板高度相似（疑似面板级复用/拼接）",
                    description=(
                        f"图 {hit['figure_a']} 的面板 {hit['panel_a']} 与 "
                        f"图 {hit['figure_b']} 的面板 {hit['panel_b']} 感知哈希几乎一致"
                        f"（hamming={hit['distance']}），提示同一面板可能被复用或拼接。"
                    ),
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Visual", source_location=doc.paper_id,
                        quote=f"{hit['figure_a']}[{hit['panel_a']}] ≈ {hit['figure_b']}[{hit['panel_b']}]",
                        basis="原文")],
                    detection_method="RegionReuse",
                    confidence_score=confidence_score(evidence=["RegionReuse"]),
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

        # --- 条带级 ELA BandELA (FREE, soft signal) ---
        # 按水平条带(泳道)分别做 ELA；被拼接/挪动的泳道与相邻未编辑泳道的
        # 重压缩误差特征不同，表现为相对整图条带中位数的异常高值。
        if doc.images:
            detectors_run.append("BandELA")
            for img_id, img in doc.images:
                scan = band_ela_scan(img)
                for lane in scan["flagged"]:
                    _mk_finding(
                        findings,
                        finding_type=["Image_Manipulation"],
                        title="条带级 ELA 异常（疑似局部拼接/编辑）",
                        description=(
                            f"图片 {img_id} 的第 {lane['band']} 条带 ELA 均值 "
                            f"{lane['ela_score']:.2f}（整图条带中位数 {scan['median_ela']:.2f}），"
                            "提示该条带可能被单独编辑过。"
                        ),
                        severity="Medium",
                        evidence_pack=[EvidencePack(
                            type="Visual", source_location=doc.paper_id,
                            quote=f"band={lane['band']}, ela={lane['ela_score']:.2f}, median={scan['median_ela']:.2f}",
                            basis="原文")],
                        detection_method="BandELA",
                        confidence_score=confidence_score(evidence=["BandELA"]),
                    )

        # --- 泳道级重复 LaneReuse (FREE, hard evidence) ---
        # 固定网格切不到"条带被复制到另一泳道"的造假（Pfizer 认定的 Yin 案例
        # 即为此类）。把图切成水平带(膜)再切成竖直泳道，逐泳道做像素级比对：
        # 相关系数门控 + 像素差异确认，双重判据压制误报。
        # 同一伪造泳道常被复制到多个目标（星形网络），逐对输出会把 62 个
        # 证据对变成 62 条 finding；先做连通聚类，每个"重复泳道网络"只报一条。
        if doc.images:
            detectors_run.append("LaneReuse")
            hits = detect_lane_reuse(dict(doc.images))
            for cl in cluster_lane_hits(hits):
                p = cl["best_pair"]
                n_mem, n_pairs = cl["n_members"], cl["n_pairs"]
                if n_mem == 2 and n_pairs == 1:
                    title = "泳道像素级几乎一致（疑似条带被复制/重复使用）"
                    desc_head = (
                        f"图 {p['figure_a']} 第 {p['band_a']} 带第 {p['lane_a']} 泳道 "
                        f"(x={p['box_a'][0]}-{p['box_a'][2]}) 与 "
                        f"图 {p['figure_b']} 第 {p['band_b']} 带第 {p['lane_b']} 泳道 "
                        f"(x={p['box_b'][0]}-{p['box_b'][2]})"
                    )
                else:
                    title = "多条泳道像素级几乎一致（疑似同一条带被复制成簇）"
                    figs = "、".join(cl["figures"])
                    desc_head = (
                        f"共 {n_mem} 条泳道（图 {figs}）两两像素高度相似，"
                        f"形成 {n_pairs} 个证据对；最强证据："
                        f"图 {p['figure_a']} 第 {p['band_a']} 带第 {p['lane_a']} 泳道 ↔ "
                        f"图 {p['figure_b']} 第 {p['band_b']} 带第 {p['lane_b']} 泳道"
                    )
                _mk_finding(
                    findings,
                    finding_type=["Image_Manipulation"],
                    title=title,
                    description=(
                        f"{desc_head} 像素相关系数 {p['correlation']}、"
                        f"像素中位差 {p['pixel_diff']}，提示条带可能被复制到不同泳道。"
                    ),
                    severity="High",
                    evidence_pack=[EvidencePack(
                        type="Visual", source_location=doc.paper_id,
                        quote=f"cluster=({cl['n_members']} lanes/{cl['n_pairs']} pairs), "
                              f"corr={p['correlation']}, diff={p['pixel_diff']}",
                        basis="原文")],
                    detection_method="LaneReuse",
                    confidence_score=confidence_score(evidence=["LaneReuse"]),
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
            no_findings_reason=None if findings else "未发现显著异常信号。",
            hallucination_check="所有信号基于确定性算法(GRIM/Benford/p-curve/pHash/ELA)与规则提取，无模型自由推断。",
            missing_info=(
                "联网检测（DOI/撤稿核查）、NLI、批量扫描、PDF 报告为 Pro 扩展（paperdetective-pro），"
                "当前未安装；"
            ) + "PDF 内嵌图片提取将在后续版本接入。",
            external_knowledge_disclaimer="PRO 扩展的联网检测依赖外部公开服务（如 doi.org）。"
            if pro else "无",
        ),
    )
