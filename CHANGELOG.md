# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/).

## [0.5.0] - 2026-08-06

### Changed
- **RegionReuse 重写：多尺度网格 + 纹理过滤 + 分档阈值**。8 个官方认定造假案例（ORI / Rice 调查 / Pfizer 声明）驱动的升级：
  - **纹理方差过滤**：弃用内容占比阈值（`MIN_CONTENT_RATIO`），改用灰度标准差（`TEXTURE_MIN_STD=6.0`）。浅色 western-blot 面板虽暗色像素占比极小，但纹理方差显著，不再被误当空白丢弃——这是 v0.4.0 漏检 Yin et al. PLOS ONE 案例的根因
  - **多尺度网格**：`GRID_RESOLUTIONS = [(3,3),(4,4),(6,8)]` 叠加切分。面板布局因论文而异，6×8 细网格能抓到跨图条带级重复（Pfizer 认定的 Yin et al. 2012 PDK-1 Fig1/Fig2 重复即由此命中）
  - **分档阈值**：6×8 细网格 tile 更小、噪声更多，hamming 阈值收紧至 ≤3；粗网格维持 ≤6。实证：单一阈值下 6×8 引入大量跨图假命中，分档后 7/8 案例命中且高置信命中正对应官方认定位置
- **案例驱动验证矩阵**：新增 8 篇官方认定造假论文（Brand 2013 / Lukianova-Hleb 2012 / Yin×2 / Bo-Yu×2 / Lipid 2014 / ZMARF 2014）全量回放，RegionReuse 在 7/8 案例命中（唯一漏检为 miR-221 案例的带级重复不对齐网格），高置信命中均落在 ORI/Rice/Pfizer 认定位置（如 Brand Fig6↔Fig7 d=0 精确重复）

### Added
- 案例库文档：`docs/case-studies/corpus-2026-08.md`（8 案例矩阵、来源、命中/漏检分析）

### Fixed
- 版本号不一致：`__init__.py` 落后于 `pyproject.toml`，统一为 0.5.0

### Tests
- 99 项全绿（RegionReuse 新增多尺度网格 / 纹理过滤 / 分档阈值 3 项测试）

## [0.4.0] - 2026-08-06

### Added
- **PDF 内嵌图片自动提取**：`ingest.py` 现在会从 PDF 页面提取内嵌图片（pypdf），并**自动过滤页面占位图**（按"页"粒度统计：同一内容指纹出现在 ≥80% 页面的即页面装饰/水印/整页栅格，另加尺寸带过滤 >4000px / <100px）。此前 PLoS 等期刊 printable 版 PDF 每页嵌入同一整页栅格，会触发 pHash 上百条全误报
- **RegionReuse 检测器**（FREE, hard evidence）：面板级图片取证。大图按 3x3 网格切分、小图按空白投影切分，分别做感知哈希，跨图/跨面板比对。首个实战命中：Brand et al. 2013 (PLoS ONE 8:e71518) 的 Figure 6 底部两格被 ORI 认定伪造（6B/6C）——整图 pHash 不可见，面板级命中
- **BandELA 检测器**（FREE, soft signal）：条带级错误水平分析。按水平泳道分别做 ELA，相对整图条带中位数 2x 以上或局部误差集中的泳道标记为可疑（拼接/编辑特征）

### Fixed
- `split_panels` 裁剪索引 bug（列区间误用于行轴）
- 页面占位图误报（见上，0.4.0 核心修复）

### Tests
- 97 项（新增 region_reuse / band_ela / furniture-filter 测试）

## [0.3.0] - 2026-08-04

### Changed
- **Free/Pro 分仓**：联网付费逻辑（DOI 解析、撤稿核查）从 MIT 核心移出，进入私有扩展 `paperdetective-pro`
- **插件机制**：新增 `plugins.py`，通过 `paperdetective.pro` entry-point 在运行时加载 Pro 扩展；未安装时 `--pro` 优雅降级为免费模式
- **移除**：`detect/citation_fraud.py` 及其测试迁移至 `paperdetective-pro` 仓库

## [0.2.0] - 2026-08-04

### Fixed
- **GRIM 算法改正**：原实现检查 `mean*n` 是否为 0.01 的倍数，凡两位小数均值都必然"通过"，检测形同虚设。现已改为正确的 GRIM 语义（Brown & Heathers 2017）：最近整数总分除以 n 后按报告精度舍入必须复现报告均值
- **跨论文查重误报**：同一篇论文内部的图片重复不再被标记为 `cross-paper`，且重复结果不再随论文对数重复上报
- **Benford 空输入误报**：没有可用数字时返回"不适用"，不再标记为造假信号
- **ELA 噪声误报**：新增 8x8 分块空间集中度判据——高噪声图片全局误差高但分布均匀，不再误报；真正的篡改表现为局部误差集中
- **CLI 目录输入崩溃**：`--input` 现在真正支持目录（递归收集支持的文件）
- **CLI 单文件容错**：单个文件解析失败不再导致整批分析崩溃
- **`--pro` 安慰剂**：PRO 模式现在真正启用 DOI 联网存在性校验，不再只改元数据
- **ingest 文件句柄泄漏**：图片文件改为上下文管理器打开；`.doc` 明确报错提示转换为 `.docx`
- **构建失败**：补齐 pyproject.toml 声明的 `README.md` 与 `CHANGELOG.md`

### Changed
- **pHash 性能**：DCT 从纯 Python 四重循环改为 scipy 向量化实现，提速约 300 倍（位级结果一致）
- **跨论文查重性能**：每张图的感知哈希从"每对论文算一次"改为"只算一次"
- **管线接入**：已实现的 Free 检测器（Benford / pHash / ELA / 跨论文查重）全部接入 `run_detection` 主管线
- **均值声明识别**：GRIM 正则新增英文 `mean=` / `M=` 写法，兼容 `mean=1.33, sd=0.5, n=30` 格式
- **Benford 最小样本量**：管线内低于 20 个数字时不触发，避免小样本噪声误报
- **CLI 输出美化**：彩色检测摘要面板（遵循 `NO_COLOR` 约定）
- **Markdown 报告美化**：元数据表、严重度统计表、🔴🟡🟢 分级图标、按严重度排序、证据引用块

### Added
- 新增 15 项回归/功能测试（总计 93 项）
- GitHub Actions CI（Python 3.10–3.13 矩阵）

## [0.1.0] - 2026-08-04

### Added
- 初始版本：六类检测模块、置信度引擎、方法仲裁、JSON/Markdown 报告
