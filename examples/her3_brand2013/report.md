# 🔍 PaperDetective 检测报告

| 项目 | 内容 |
| --- | --- |
| 引擎 | PaperDetective v1.0 |
| 分析时间 | 2026-08-06T10:20:09.595284+00:00 |
| 运行模式 | 🆓 Free |
| 状态 | success |
| 检测器 | BandELA, Benford, ELA, GRIM, RegionReuse, pHash |
| 论文 | paper |

---

## ⚠️ 结论：发现 **2** 项可疑信号

| 🔴 高 | 🟡 中 | 🟢 低 |
| :---: | :---: | :---: |
| 1 | 0 | 1 |

---

## 发现明细

### 🔴 高 `FD-002` 子图面板高度相似（疑似面板级复用/拼接）

- **类型**：Image_Manipulation
- **检测方法**：RegionReuse
- **置信度**：0.90
- **说明**：图 page6_Im3.png 的面板 r3c1 与 图 page6_Im3.png 的面板 r3c2 感知哈希几乎一致（hamming=6），提示同一面板可能被复用或拼接。
- **证据**：

  > 📍 `paper`（Visual）
  > page6_Im3.png[r3c1] ≈ page6_Im3.png[r3c2]


### 🟢 低 `FD-001` 数字首位分布偏离 Benford 定律

- **类型**：Data_Fabrication
- **检测方法**：Benford
- **置信度**：0.50
- **说明**：文本中 1854 个数字的首位分布与 Benford 期望的最大偏差 0.141（首位 1 占比 26.5%，期望约 30.1%），提示数字可能经人工编造。
- **证据**：

  > 📍 `paper`（Data）
  > n=1854, deviation=0.1409

---

> ⚖️ **免责声明**：检测结果是筛查信号而非法证定论，可能存在误报/漏报；不得作为对论文或作者学术不端的唯一判定依据，建议结合领域专家复核。
>
> ℹ️ 联网检测（DOI/撤稿核查）、NLI、批量扫描、PDF 报告为 Pro 扩展（paperdetective-pro），当前未安装；PDF 内嵌图片提取将在后续版本接入。
