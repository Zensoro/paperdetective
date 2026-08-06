# 🔍 PaperDetective

**论文内容级学术打假检测器** — 对论文进行数据造假、图片操纵、引用造假、撤稿标记、内文自悖、跨论文重复六类信号筛查，输出严格的结构化报告。

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-99%20passed-brightgreen)](#-测试)

> ⚖️ **免责声明**：本工具的检测结果是**筛查信号**而非法证定论，可能存在误报/漏报；不得作为对论文或作者学术不端的唯一判定依据，请务必结合领域专家复核。

---

## ✨ 特性

| 检测模块 | 方法 | 证据级别 | 运行模式 |
| --- | --- | --- | --- |
| 数据造假 | **GRIM**（均值×样本量整数一致性）、Benford 首位分布、p-curve | 硬证据 / 软信号 | 🆓 Free |
| 图片操纵 | pHash 感知哈希（文内图复用）、ELA 错误水平分析、**RegionReuse** 面板级复用（多尺度网格）、**BandELA** 条带级错误水平分析 | 硬证据 / 软信号 | 🆓 Free |
| 跨论文重复 | 跨文档 pHash 比对、数据指纹 | 硬证据 | 🆓 Free |
| 引用造假 | DOI 格式校验 + doi.org 存在性解析 | 硬证据 | 💎 PRO 扩展 |
| 撤稿标记 | 撤稿关键词 / 元数据交叉核查（可插拔） | 硬证据 | 💎 PRO 扩展 |
| 内文自悖 | 数值主张相对偏差比较（NLI 可插拔） | 软信号 | 🆓 Free |

- **确定性算法**：所有结论基于确定性算法与规则提取，无模型自由推断，无幻觉风险
- **案例驱动开发**：检测器由官方认定的真实造假案例（ORI / Rice 调查 / Pfizer 声明）驱动迭代，[8 案例验证矩阵](docs/case-studies/corpus-2026-08.md) 保证高置信命中对应官方认定位置
- **分层置信度引擎**：硬证据 0.85+，软信号按 corroboration 分层，内部知识一律封顶 0.60
- **严格 schema**：输出 Pydantic 校验的 JSON 报告，同时支持美化 Markdown 导出
- **批量处理**：支持目录输入，单文件失败不影响整批
- **离线可用**：Free 层全部本地运行；联网 PRO 能力由可选扩展 `paperdetective-pro` 提供

## 🚀 安装

```bash
pip install -e .                # 核心功能
pip install -e ".[pdf,docx]"    # PDF / Word 支持
pip install -e ".[dev]"         # 开发（pytest）
pip install paperdetective-pro  # 付费扩展（解锁 --pro 联网检测）
```

> 🔒 **开源/付费分仓**：本仓库（MIT）只含免费核心。联网检测（DOI 解析、撤稿交叉
> 核查、NLI、批量、HTML/PDF 报告）在私有扩展 `paperdetective-pro` 中，通过
> `paperdetective.pro` entry-point 按需加载；未安装时 `--pro` 优雅降级为免费模式。

## 📖 快速开始

```bash
# 分析单个文件（输出 JSON）
paperdetective analyze --input paper.pdf

# 批量分析整个目录，输出 Markdown 报告
paperdetective analyze --input ./papers/ --markdown --output report.md

# PRO 模式：启用联网 DOI 存在性校验
paperdetective analyze --input paper.pdf --pro
```

支持格式：`.txt` / `.pdf` / `.docx` / `.png` / `.jpg` / `.jpeg` / `.gif` / `.bmp`

### Python API

```python
from paperdetective.ingest import ingest_path
from paperdetective.analyze import run_detection
from paperdetective.report import to_markdown

docs = [ingest_path("paper.pdf")]
result = run_detection(docs, pro=False)
print(to_markdown(result))
```

### GRIM 检测示例

整数数据（如 Likert 量表）的均值与样本量必须满足整数一致性：
报告 `均值=2.66, n=2` 时，总分只能是整数 5 或 6（对应均值 2.5 或 3.0），
2.66 在数学上不可能存在 → **GRIM 违规（硬证据，置信度 0.90）**。

## 🏗️ 架构

```
输入 (PDF/Word/图片/文本, 支持批量)
    ↓
Phase A: ingest.py          — 文本/图片抽取，统一为 Document
    ↓
Phase B: detect/            — 六类检测器（纯函数，可独立测试）
         engine/            — 置信度分层 · 方法冲突仲裁 · 三角验证
    ↓
Phase C: analyze.py → report.py — 管线编排，输出 JSON / Markdown
```

```
paperdetective/
├── ingest.py            # 输入抽取（txt/pdf/docx/图片）
├── analyze.py           # 检测管线编排
├── report.py            # Markdown 报告渲染
├── schemas.py           # Pydantic 报告 schema
├── plugins.py           # Pro 扩展加载（entry-point）
├── eval.py              # gold 标注评估（precision/recall/F1）
├── detect/              # 数据造假 · 图片操纵 · 内文自悖 · 跨论文重复
└── engine/              # 置信度引擎 · 仲裁 · 三角验证
```

Pro 扩展独立于本仓库：`paperdetective-pro`（私有/付费），含 DOI 解析、撤稿核查、
NLI、批量扫描、报告导出，注册 `paperdetective.pro` entry-point 后自动接入管线。

## ✅ 测试

```bash
python -m pytest        # 99 项测试
```

## 📚 案例库

检测器由**官方认定的真实造假论文**驱动迭代（案例驱动开发）：

| 案例 | 来源 | RegionReuse 命中 |
| --- | --- | --- |
| Brand et al. 2013 (HER3 western-blot) | ORI 认定 | ✅ Fig6↔Fig7 d=0 精确重复 |
| Lukianova-Hleb et al. 2012 (plasmonic nanobubbles) | Rice 调查 | ✅ Fig3 内部重复 |
| Yin et al. 2012 (PDK-1) | Pfizer 声明 | ✅ Fig1/Fig2 跨图重复 |
| Yin & Nassirpour 2013 (miR-221) | Pfizer 声明 | ⚠️ 漏检（带级重复不对齐网格） |
| Bo-Yu et al. 2014 (ANGPTL4) | ORI 认定 | ✅ |
| Bo-Yu et al. 2013 (dendritic) | ORI 认定 | ✅ |
| Lipid 2014 (PLoS ONE 11:111253) | 撤稿 | ✅ |
| ZMARF 2014 (PLoS ONE 9:94830) | 撤稿 | ✅ |

→ 完整矩阵与命中/漏检分析见 [docs/case-studies/corpus-2026-08.md](docs/case-studies/corpus-2026-08.md)

## 🗺️ Roadmap

- [x] PDF 内嵌图片自动提取
- [x] RegionReuse 面板级图片取证（多尺度网格 + 纹理过滤）
- [x] BandELA 条带级错误水平分析
- [ ] SPRITE 完整实现接入管线
- [ ] Pro 扩展：撤稿数据库（Retraction Watch / Crossref）交叉核查
- [ ] Pro 扩展：NLI 内文自悖（LLM 可插拔）
- [ ] Pro 扩展：HTML / PDF 报告导出
- [ ] Web 界面

## 📄 License

MIT — 本仓库（免费核心）见 [LICENSE](LICENSE)。

联网付费能力（DOI 解析、撤稿核查、NLI、批量、报告导出）属于私有扩展
`paperdetective-pro`，采用专有许可证，不随本仓库分发。
