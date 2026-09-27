# PeakBot 独立核实记录

**核实日期：** 2026-09-26  
**状态：** 官方源码与示例已独立获取；隔离环境建立；单个真实 mzML 文件解析与预训练权重 API smoke 通过；尚未生成 PeakBot 候选峰或计算任何数据集指标。  
**用途：** 在不改动 `E:\论文\B0\cnn` 原项目、既有实验和封存测试集的前提下，判断 PeakBot 是否能作为真实 LC–HRMS 峰检测/定位的可复现对照。

## 原始论文与官方代码

- 论文：Bueschl et al., *PeakBot: machine-learning-based chromatographic peak picking*, Bioinformatics, 2022。 [PubMed](https://pubmed.ncbi.nlm.nih.gov/35604083/) · [全文](https://pmc.ncbi.nlm.nih.gov/articles/PMC9237678/) · [DOI](https://doi.org/10.1093/bioinformatics/btac344)
- 官方模型仓库：[christophuv/PeakBot](https://github.com/christophuv/PeakBot)
- 作者示例与预训练权重仓库：[christophuv/PeakBot_Example](https://github.com/christophuv/PeakBot_Example)
- 作者公布的原始数据获取说明在示例仓库的 [`READMEData.md`](https://github.com/christophuv/PeakBot_Example/blob/main/READMEData.md)。该说明指出原始数据不随 Git 仓库发布，需要从对应数据集取得并按需要转换。

## 本地独立副本

```text
E:\论文\PeakBot_可复现性核实_2026-09-26\
├─ README.md
└─ source\
   ├─ PeakBot\
   └─ PeakBot_Example\
```

两个仓库均以浅克隆方式获取，当前检出版本：

| 仓库 | Git 提交 |
|---|---|
| PeakBot | `c5df4f0d12db5165cd8714bebbe8941cc4c8bfc5` |
| PeakBot_Example | `24ff3e2561018a2a71584c2cccbb42a154188012` |

示例仓库包含 5 个 HDF5 预训练模型（合计约 116.1 MB）。SHA-256：

| 权重 | SHA-256 |
|---|---|
| `PBmodel_MTBLS1358.model.h5` | `61c4ffa18e839ff37a2664052f23ee751608e61ca00d9e6f484b94fcdb15170d` |
| `PBmodel_MTBLS797.model.h5` | `d3410aa1ef92e1b552130035c44a2bd705ce68610ae22ac1aac9c37fbf19ddbc` |
| `PBmodel_MTBLS868.model.h5` | `b09207a98b5b7fcc9c650748cd54a1181c76cfc95190be7caffce350f84602ae` |
| `PBmodel_PHM.model.h5` | `d54faa80649cb5d10dc1f387c886cccd36993fb7cc19511d2413410fe4881659` |
| `PBmodel_WheatEar.model.h5` | `b209fb06133d61d618280194967662e4452d61a1d1ea2e4df69b7e268188a684` |

## 初步技术审查

PeakBot 是面向 **LC–HRMS profile-mode 原始质谱**的峰拾取系统：从原始扫描建立局部极大值候选，将其表示成 RT × m/z 的二维区域，再由 CNN 输出峰类别、中心和边界框。官方实现配置的输入网格为 32 × 128；训练流程要求真实参考峰、背景/干扰区及仪器处理参数。示例文档建议准备至少约 100 个参考特征。

这与本项目 B0/B1-Dual 的一维 EIC 二分类不是同一输入任务。不能把二维原始谱伪造成一维信号后声称是原版 PeakBot 对比，也不能仅凭预训练模型在未匹配数据上的分数作为峰位精度证据。

不过，当前 E 盘 Zenodo 数据压缩包 `E:\论文\zenodo\A_dataset_for_evaluation_of_peak_detection_methods_v3.zip` 内可见 **51 个 mzML 文件，原始文件解压总体积约 4.93 GB**；PeakBot 源码提供 mzML 解析路径。因此具备检查原始二维输入的基础，不必先把 mzML 强行改造成一维 EIC。下一道关键门槛是：将验证集特征、mzML 样本、m/z 与 RT 区域，以及可用于峰中心/边界评价的标注可靠映射起来，并保证训练/调参只用训练/验证部分。

## 已完成的本地 smoke（不等同于实验结果）

本目录中的独立运行环境：`runtime\peakbot-py38`；当前解析快照见 [`runtime/requirements-freeze-2026-09-26.txt`](runtime/requirements-freeze-2026-09-26.txt)。使用 Python 3.8.20、TensorFlow 2.5.0、NumPy 1.19.5、Numba 0.53.1、pandas 1.2.3、SciPy 1.7.3、pymzML 2.5.0；其他传递依赖以本机 `uv` 当时解析结果为准，不应声称与作者完整 Anaconda 环境逐包完全相同。TensorFlow 在这台 Windows 机器上实际回退到 CPU（检测到 GTX 1650 Ti，但缺少 CUDA 11/cuDNN 运行库）。

结果见 [`results/smoke_v1/report.json`](results/smoke_v1/report.json)，复现入口为 [`scripts/peakbot_mzml_smoke.py`](scripts/peakbot_mzml_smoke.py)。对 Zenodo 包中单个样本 `161010_10_Stich_14_T.mzML` 的检查结果：解析到 2,524 个 MS1 scans，RT 范围约 0.221–1,471.002 秒；作者提供的 MTBLS1358 checkpoint 可加载，32 × 128 dummy tensor 的三个输出形状分别为 `[1,6]`、`[1,2]`、`[1,4]`，数值有限。该检查**没有**把该 dummy tensor 当成色谱区域，没有读取标签、产生真实候选、计算验证指标或接触测试集。

试跑还发现官方解析代码与当前 `pymzML 2.5.0` 的扫描时间键不匹配：源码取 `spectrum["scan time"]`，但这个 mzML 文件提供的是 `scan start time`（单位 minute）。核实脚本只在隔离 smoke 入口里增加了一个透明兼容 shim，再由官方解析器的 `×60` 转成秒；**官方克隆源码未修改**。正式实验前必须进一步验证该 RT 映射对全部目标文件/扫描均正确，并将 shim 作为明确的复现适配记录，不能静默改动。

## 环境与许可证注意事项

- 官方环境文件采用 Python 3.8 / TensorFlow 2.5 系列；本机当前 Python 为 3.14，且没有 TensorFlow、Numba、pymzml 或 HDF5 运行依赖，不能直接运行官方模型。**没有在系统 Python 或原项目环境中安装/升级依赖。**
- 两仓库的 `LICENCE` 文件标示 CC BY-NC-SA 4.0。用于论文前需确认非商业使用、署名及可能的衍生作品共享条款适用性；不要把源码或修改版直接并入主项目。
- GitHub 上的示例权重可用，但示例 README 明确原始数据不包含在代码仓库中。预训练权重对应其各自来源数据集，不等于已在本 Zenodo 任务上完成有效对照。

## 后续验证门槛

1. 记录并冻结当前隔离环境依赖；如要严格复现，优先按官方环境 YAML 再建立一套逐包锁定环境。
2. 先核对 Zenodo 验证集 feature 到原始 mzML 文件及 RT/m/z 区域的映射。不得查看或用于选择模型的最终测试集。
3. 以真实 32 × 128 RT × m/z 候选区域运行预训练模型，固定权重及哈希，确认候选构造、输出中心/边界与 RT 单位正确；当前 dummy 推理不满足这项要求。
4. 只有当真实标签能对齐到 PeakBot 检测对象、评价单位和匹配规则可预先固定时，才进入验证集对照；若原数据只支持 EIC 有/无峰标签，则仅报告检测指标，不得声称真实峰位精度比较。
5. 固定全部转换、阈值和匹配规则后，才允许进行一次最终测试；最终测试集不得用于参数选择。

## 当前结论

PeakBot 值得继续做 **真实原始 mzML 的独立可行性核实**，因为项目数据包确有原始谱文件且官方解析器支持 mzML；目前已证明隔离环境能载入作者权重并解析一个真实文件（需透明处理 scan-time 键差异）。但目前还**没有完成真实候选峰推理、标签映射或对照实验**，也没有真实定位结果。能否成为论文中的定位基准，取决于验证集原始文件映射与可靠位置标签能否闭合。若标签无法提供可审计的峰中心/边界，PeakBot 可作为峰检测对照，但不能用于证明我们模型的定位优势。
