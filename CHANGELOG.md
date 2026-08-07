# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/).

## [Unreleased]

### Added
- **`paperdetective.tools.dump_lane_dataset`**：用确定性 LaneReuse 检测器作**高置信自动标注器**，把语料库每篇 PDF 的每个 western-blot 泳道切出并打标，导出可训练数据集。三类标签 `duplicate` / `clean_lane` / `rejected`，按 `fraud` / `control` 分 split（对照组留作测试集）；产出 `images/*.png` + `manifest.csv`（几何/熵/能量/最相关 corr 等特征）+ `pairs.csv`（真实重复对作正样本、同论文 clean↔clean 抽样作负样本，供孪生网络训练）。这是"为将来神经网络"铺路的第一步——在尚无 100+ 标注样本前，先让确定性算法自动攒数据。详见 `paperdetective/tools/README.md`。
- **语料库多 split 布局 + 标签强度分层**：`--corpus` 下每个子目录自成一个 split，避免不同可信度的标签被拉平成同一档。顶层 PDF = `fraud`（金标准：ORI/机构调查/申办方声明**逐图认定**），`retracted/` = `retracted`（弱标签：因图像问题撤稿，但无逐图官方认定），`clean/` = `control`（负对照，`clean` 别名保持向后兼容）。只有 `fraud` 档的 `duplicate` 标签能对照已发表认定核验；`retracted` 档用于扩充训练量，**不可用作衡量精确率的真值**。
- **数据集扩充管线**（Retraction Watch → 开放获取 PDF → dump）：以 Crossref Labs 免费托管的 Retraction Watch 撤稿库（7.1 万条）为标签源，按图像类撤稿原因码（`Duplication of/in Image` 等）筛出 1681 条图像类撤稿，交叉 PLoS ONE 开放获取得 459 篇候选，批量下载后并入 `retracted` split。

## [0.6.0] - 2026-08-06

### Added
- **LaneReuse 检测器**（FREE, hard evidence）：泳道级图片取证。把图片切分成水平条带（膜）再切分成竖直泳道，逐泳道做像素级比对：Pearson 相关系数门控（≥0.95）+ 像素中位差确认（≤12）双重判据。命中官方认定造假 8/8：
  - **Brand et al. 2013 (PLoS ONE 8:e71518, ORI)**：Fig6/Fig7 跨图条带重复，51 对 → 15 簇
  - **Yin/Nassirpour et al. 2013 (PLoS ONE 8:e62170, Pfizer)**：Figure 6 blot 泳道三连重复（b6 带泳道 2/5/8 + 3/9），这正是 v0.5.0 中 RegionReuse 漏检、Pfizer 声明认定的 "duplicated bands inside western blots"
  - **Bo-Yu et al. 2014 (ANGPTL4)**：52 对 → 18 簇，最大簇 11 条泳道横跨 3 张图
- **hit 聚类聚合**：同一伪造泳道常被复制到多个目标（星形网络），逐对输出会把 62 个证据对变成 62 条 finding。Union-Find 连通聚类把互相链接的泳道折叠为簇，每个"重复泳道网络"只报一条 finding（并给出成员数/证据对数/最强相关系数）
- **对照组方法论**：新增 3 篇方法学/综述类论文（2022 辅助犬 PTSD、2016 腺苷镇痛 meta、2016 梦游 meta）作为**无 WB 图稿对照组**。它们从未参与参数调优，用于验证 LaneReuse 无误报

### Changed
- **LaneReuse 双重预过滤**（对照组驱动，case-driven 调优的一部分）：
  - **条带高度下限 `LANE_MIN_H=100`**：图表碎片（森林图标记、流程图边框、图例刻度）被空白投影误切成"泳道"，高度门控直接丢弃
  - **泳道灰度熵下限 `LANE_MIN_ENTROPY=1.0`**：真实 blot 泳道有纹理信号（熵 ~1-4）；近空白条带（流程图边框等）熵 <1.0。无此过滤时对照组产生 1-5 个假簇，加入后 3/3 对照组零误报且 8/8 造假案例全部保持命中
- **诚实记录 case-driven 调优边界**：LaneReuse 的阈值（corr/diff/height/entropy）是在 8 个官方认定造假案例上调出来的——即"训练集"上 100% 命中。对照组实验的意义在于：**从未参与调参的独立论文**上零误报，降低了过拟合风险，但不能声称已解决

### Fixed
- 版本号不一致：`__init__.py` 落后于 `pyproject.toml`，统一为 0.6.0

### Tests
- 111 项全绿（LaneReuse 新增聚类 3 项 + 熵门控 / 高度门控 / 门控回归 3 项测试）

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
