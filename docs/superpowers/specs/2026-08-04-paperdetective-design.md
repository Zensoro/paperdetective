# PaperDetective v1.0 设计文档

- 日期: 2026-08-04
- 状态: 已确认设计（待实现）
- 定位: 开源学术打假 agent 系统（GitHub: Zensoro/paperdetective）

## 1. 项目背景

对标 GitHub 竞品 `apifyforge/research-integrity-screening-mcp`（研究者级元数据筛查），
PaperDetective 专注**论文内容级**造假检测，形成互补而非竞争关系。

竞品能力边界（来自 README 分析）:
- 研究者级: 引用分布异常、论文工厂模板、期刊质量、资助风险
- 基于外部元数据: OpenAlex / ORCID / PubMed / Semantic Scholar / Crossref / CORE / NIH
- 无图片检测、无内容级数据检测、无引用存在性验证
- 付费 $0.045/次

## 2. 目标与定位

**PaperDetective = 论文内容级学术打假 agent**

- 输入: PDF / Word / 图片 / 纯文本（可批量）
- 输出: 严格 JSON 结构化报告（可导出 PDF/HTML）
- 检测: 六大检测模块 + 三个原创复合检测链
- 形式: 独立完整 agent（本地 LLM 推理，可离线运行图片/数据/文本检测）
- 差异化卖点: "数据-图表-文本"三角验证链、分层置信度引擎、方法冲突仲裁

## 3. 整体架构（三阶段管线）

```
输入 (PDF/Word/图片/文本, 支持批量)
    ↓
┌─────────────────────────────────┐
│ Phase A: Extraction 信息抽取      │
│  - 数据提取（表格、统计值）        │
│  - 图片提取（图表、照片）          │
│  - 引用提取（DOI、文献列表）       │
│  - 文本提取（摘要、正文）          │
└─────────────────────────────────┘
    ↓ 结构化中间产物
┌─────────────────────────────────┐
│ Phase B: Detection 问题检测       │
│  ① 数据造假检测（本地）           │
│  ② 图片造假检测（本地）           │
│  ③ 引用造假检测（本地+联网）      │
│  ④ 撤稿交叉检测（联网）           │
│  ⑤ 内文自悖检测（本地）           │
│  ⑥ 跨论文重复检测（本地,多篇）    │
│  + 复合检测链（三角验证/置信度/仲裁）│
└─────────────────────────────────┘
    ↓ 问题清单（附证据）
┌─────────────────────────────────┐
│ Phase C: Evidence Backtracking   │
│  - 证据回溯（页码/图号/表号）     │
│  - 置信度评分                    │
│  - JSON 校验（自检）              │
│  - 报告生成（JSON + Markdown）    │
└─────────────────────────────────┘
    ↓
输出 (JSON 报告 + Markdown + 可导出 PDF/HTML)
```

## 4. 六大检测模块

### 4.1 数据造假检测（本地）
- **GRIM 测试**: 均值 × 样本量 必须与数据粒度整除，否则数据必为编造
- **SPRITE 测试**: 标准差与均值、样本量的内部一致性
- **p-curve 分析**: p 值分布是否异常集中在 0.05 附近（p-hacking）
- **Benford 定律扩展**: 首位/末位/数字对分布多维度检验

### 4.2 图片造假检测（本地）
- **ELA 误差水平分析**: JPEG 压缩残差检测 PS 痕迹
- **PRNU 噪声指纹**: 传感器固定噪声一致性检测拼接/克隆
- **感知哈希 (pHash/dHash)**: 图片相似度快速比对

### 4.3 引用造假检测（本地+联网）
- DOI 存在性验证（Crossref API）
- 文献真实存在性验证（OpenAlex API）
- 引用与内容匹配验证（NLI）
- **同源幻觉引用检测**: 识别 AI 编造的"看起来真实"的引用模式

### 4.4 撤稿交叉检测（联网）
- 标题/DOI 查重，检查撤稿标记（retracted / correction / erratum / expression of concern）
- 数据源: OpenAlex + Crossref（免费 API）

### 4.5 内文自悖检测（本地）
- 摘要 vs 正文 vs 结论 数据比对
- NLI 数值推理: 前提 → 结论 自洽性验证
- 表格数据与叙述文本交叉验证

### 4.6 跨论文重复检测（本地, 需多篇）
- 感知哈希 + 图像嵌入向量（CLIP 类模型）跨论文图片比对
- 数据分布指纹跨论文比对（可抓"换了滤镜"的重复图）
- 输出: 跨论文重复对清单

## 5. 原创复合检测链（差异化卖点）

### 5.1 「数据-图表-文本」三角验证链
```
图表反推数值 ──比对──> 文中声称数值 ──比对──> 统计数据
任一环不一致 = 造假信号
```
- 图表数值反推: 从图表像素反推条形高度/数据点
- 三角闭环验证: 图表↔文本↔统计 三方交叉

### 5.2 分层置信度引擎
| 置信度区间 | 证据类型 |
|---|---|
| 0.85 - 1.00 | 硬证据: GRIM 失败 / PRNU 不匹配 / DOI 不存在 |
| 0.60 - 0.84 | 多软信号互相印证 |
| 0.40 - 0.59 | 单软信号: p-curve 异常 / 突发性低 |
| ≤ 0.60 上限 | 依赖模型内部知识的纵向对比 |
- 多软信号叠加 → 升级为硬证据

### 5.3 方法冲突仲裁
- 当两个检测方法结论相反时（如 Benford 正常但 GRIM 失败）
- 自动仲裁哪方可信，降低误报率
- 仲裁逻辑: 方法可靠性权重表 + 证据链完整度

## 6. 检测方法技术栈

### 6.1 统计方法（第一梯队, 全上）
- GRIM / SPRITE: 纯算法，NumPy 实现
- p-curve: scipy.stats 实现
- Benford 扩展: NumPy 实现
- 来源: 心理学领域公开方法（Brown & Heathers, 2017 等）

### 6.2 AI 方法（第二梯队, 选 3 个）
- 图表数值反推: 图像处理 + 像素分析
- NLI 数值推理: 本地 LLM 推理
- 图像嵌入向量: CLIP 类模型（可选项，降级为感知哈希）

### 6.3 原创组合（第三梯队, v1.0 差异化）
- 三角验证链 / 分层置信度引擎 / 方法冲突仲裁

## 7. 输出格式（JSON Schema）

```json
{
  "analysis_metadata": {
    "papers": [{"title": "...", "authors": "...", "input_id": "..."}],
    "analysis_timestamp": "ISO 8601",
    "agent_version": "PaperDetective v1.0",
    "processing_status": "success / partial / ocr_failed"
  },
  "detected_findings": [
    {
      "id": "FD-001",
      "finding_type": ["Data_Fabrication"],
      "title": "...",
      "description": "...",
      "severity": "High / Medium / Low",
      "evidence_pack": [
        {"type": "Text/Data/Visual", "source_location": "...", "quote": "..."}
      ],
      "detection_method": "GRIM / SPRITE / p-curve / Benford / ELA / PRNU / pHash / NLI / CrossCheck / ChartReconstruct",
      "confidence_score": 0.85
    }
  ],
  "internal_review": {
    "no_findings_reason": "...",
    "hallucination_check": "...",
    "missing_info": "...",
    "external_knowledge_disclaimer": "..."
  }
}
```

### 7.1 finding_type 取值
- Data_Fabrication（数据造假）
- Image_Manipulation（图片造假）
- Citation_Fabrication（引用造假）
- Retraction_Flag（撤稿标记）
- Internal_Inconsistency（内文自悖）
- Cross_Paper_Duplication（跨论文重复）

## 8. 置信度评分标准（与检测方法绑定）

| 分数区间 | 证据标准 |
|---|---|
| 0.85 - 1.00 | 硬证据 + 完整数据链 + quote 逐字直引 |
| 0.60 - 0.84 | 多条原文证据互相印证 |
| 0.40 - 0.59 | 单条证据或关键字段缺失 |
| 0.20 - 0.39 | 主要为推断，原文仅暗示 |
| ≤ 0.60 上限 | 依赖模型内部知识的纵向对比 |

## 9. 输入/输出规格

### 9.1 输入格式
- PDF（PyMuPDF 提取文本 + 图片）
- Word .docx（python-docx 提取）
- 图片 jpg/png（直接分析）
- 纯文本（直接分析）
- 批量: 目录输入

### 9.2 输出
- JSON 报告（结构化）
- Markdown 报告（可读）
- PDF/HTML 导出（v1.0 可选）

## 10. 项目结构（对齐 archagent 模式）

```
paperdetective/
├── pyproject.toml
├── README.md / README.zh-CN.md
├── LICENSE (MIT)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .gitignore
├── .github/workflows/ci.yml
├── paperdetective/
│   ├── __init__.py
│   ├── cli.py
│   ├── api.py
│   ├── config.py
│   ├── llm.py
│   ├── ingest.py          # Phase A: 输入解析
│   ├── extract.py         # Phase A: 信息抽取
│   ├── detect/
│   │   ├── __init__.py
│   │   ├── data_fabrication.py   # ① GRIM/SPRITE/p-curve/Benford
│   │   ├── image_manipulation.py # ② ELA/PRNU/pHash
│   │   ├── citation_fraud.py     # ③ DOI/文献验证
│   │   ├── retraction.py         # ④ 撤稿交叉
│   │   ├── internal_inconsistency.py # ⑤ 内文自悖
│   │   └── cross_paper.py        # ⑥ 跨论文重复
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── triangle_verify.py    # 三角验证链
│   │   ├── confidence.py         # 分层置信度
│   │   └── arbitration.py        # 方法冲突仲裁
│   ├── evidence.py        # Phase C: 证据回溯
│   ├── schemas.py         # JSON Schema 校验
│   ├── report.py          # 报告生成
│   ├── eval.py            # 评测
│   └── prompts/           # Agent prompt 文件
├── tests/
│   ├── test_data_fabrication.py
│   ├── test_image_manipulation.py
│   ├── test_citation_fraud.py
│   ├── test_retraction.py
│   ├── test_internal_inconsistency.py
│   ├── test_cross_paper.py
│   ├── test_triangle_verify.py
│   ├── test_confidence.py
│   └── test_arbitration.py
└── docs/
    └── superpowers/specs/2026-08-04-paperdetective-design.md
```

## 11. 评测方案

- 合成黄金基准: 构造含已知造假模式的论文（对齐 archagent 的 synthetic benchmark 做法）
- 指标: 检测召回率 / 精确率 / F1
- 每类造假构造 ≥ 3 个合成样本
- 目标: 检测六类造假 F1 ≥ 0.85

## 12. 发布计划

1. v1.0.0: 六大检测模块 + 三角验证链 + 置信度引擎 + 仲裁
2. 开源发布: GitHub Zensoro/paperdetective（SSH 已配置）
3. CI: GitHub Actions 自动测试
4. 文档: 中英双语 README + CONTRIBUTING + SECURITY

## 13. 商业模式（开源核心 + 增值付费）

采用 **open-core 模式**：核心检测能力开源免费，增值能力付费。通过配置/许可密钥
（`PAPERDETECTIVE_MODE=free|pro` 或 license key）切换。

### 免费（MIT 开源核心）
- 六大检测模块的**本地**能力：GRIM/SPRITE/Benford/p-curve、ELA/pHash 图片检测、
  内文自悖（数值比对）、跨论文重复（本地指纹）
- CLI 基础用法 + JSON 报告
- 单篇论文检测

### 付费（Pro 增值）
- **联网检测**：撤稿交叉检测（OpenAlex/Crossref）、引用存在性验证（DOI 解析）
- **深度图片分析**：PRNU 传感器噪声指纹（依赖付费 API/模型）
- **批量扫描**：目录/批量论文检测
- **报告导出**：PDF/HTML 可分享报告
- **NLI 内文自悖**：本地 LLM 调用（需付费模型 API）

### 实施约束
- 代码仓库只包含免费核心 + 付费功能的**接口与占位**（无许可时返回提示）
- 联网/深度能力通过可插拔 API 客户端实现，付费通过用户自带的 API key 或订阅服务
- 免费核心保持完整可用，不做功能阉割式付费

### License Key 收款（v1.1+，决策于 2026-08-04）
- **渠道**：LemonSqueezy（个人可收款、自动开发票、支持国内外）
- **交付**：付费用户购买后获得 `PRO_LICENSE` 激活码，CLI `--pro` 时校验
- **解锁内容**：联网检测（撤稿交叉/引用验证）、批量扫描、PDF/HTML 报告导出
- **校验机制（离线优先）**：
  - 本地签名校验：激活码 = `payload.signature`（Ed25519 签名，公钥内置，私钥在服务端）
  - payload 含：license_type=pro、expiry、特征数上限
  - 离线可验真，无法防分发——接受（学术工具破解意愿低）
- **防滥用补充**：可选在线校验（首次激活时联网核对一次）+ 机器绑定（可选）
- **接口占位**：`paperdetective/license.py` 提供 `validate_license(key) -> LicenseInfo`，
  `pro` 模式下未激活返回提示而非功能

## 14. 免责声明（强制要求）

检测工具不保证 100% 正确，存在误报/漏报。必须在以下位置声明：

1. **README / README.zh-CN.md**: 醒目位置声明"检测结果是筛查信号，不是法证定论；
   可能存在误报/漏报；不得作为对作者学术不端的唯一判定依据"
2. **输出 JSON 报告**: `internal_review` 增加 `disclaimer` 字段，每条报告自动附带
3. **LICENSE**: MIT 标准免责条款（"AS IS，不承担因使用本项目造成的任何损害"）
4. **SECURITY.md / 报告页脚**: 提示结合人工专家复核

## 15. 风险与缓解

| 风险 | 缓解 |
|---|---|
| PRNU/ELA 对重压缩图片失效 | 降级为 pHash + 图像嵌入 |
| NLI 误报率高 | 仅作软信号，需其他方法印证 |
| 联网 API 不可用 | 引用/撤稿检测降级为本地启发式 |
| 误报伤害作者声誉 | 输出必须附证据链 + 置信度分级 + 免责声明 |
| 付费功能被绕过 | 付费能力走云端/API，license 校验在远端 |
| 免费核心被诟病"阉割" | 核心六类检测完整可用，付费仅增联网/深度/工程能力 |
