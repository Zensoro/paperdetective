# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/).

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
