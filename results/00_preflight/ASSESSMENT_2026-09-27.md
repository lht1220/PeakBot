# PeakBot 对 Zenodo 原始文件的数据准入结论

日期：2026-09-27。状态：**BLOCKED_INPUT_MODE**。这是输入不兼容记录，不是模型性能结果。

## 实际检查

- 原始包：`A_dataset_for_evaluation_of_peak_detection_methods_v3.zip`，4,034,166,285 字节。
- ZIP SHA256：`dcc349cd842c7540426828b8979c5b2fd349ad13526ad1878ed3a6eda947fe33`。
- 51 个 mzML，共 128,804 个已解析 spectrum；逐文件身份、谱模式与时间审计见 `zenodo_archive_20260927_v1/report.json`。
- 包中全部 51 个文件的 MS1 谱均标示 centroid (`MS:1000127`)，profile 文件数为 0。
- 扫描计数、MS level、RT 单位与单调性检查通过；两个官方源码版本、干净状态和五个模型权重哈希通过。
- 8 个标准库测试通过；本地 Python 3.8.20 运行。未安装服务器环境、未生成真实候选或计算检测/定位指标。

## 科学解释

作者 [PeakBot 官方说明](https://github.com/christophuv/PeakBot) 指定 LC–HRMS profile-mode 输入。固定源码 `src/peakbot/cpu.py` 先估计 m/z profile 特征，筛选出有 profile 峰的候选，再建立 RT×m/z 标准化输入。

这些 Zenodo mzML 可被解析，但已做质心化，并非原始 profile 数组。不能因文件扩展名是 mzML、vendor filter string 含 `p`，或预训练模型可加载，就视为满足官方前处理条件。把质心点插值/画成 profile 图也不会恢复丢失的实测峰轮廓。

本报告不声称“所有可能适配均不可行”，只是不批准把当前质心输入直接作为原版完整 PeakBot benchmark。另行改变前处理需明确称为 centroid 适配并审查公平性。

## 下一步可选路径

1. **先完成原任务运行复现**：取得作者示例的真正 profile 数据，冻结官方示例参数和 checkpoint，跑候选生成与推理。这可证明流程复现，不能证明在 Zenodo 分类任务上的性能。
2. **对同一 Zenodo 任务正式验证**：索取相同样本的 profile/raw 文件，并核实它们与当前 EIC、sample/feature 的映射。即使取得原始输入，现有专家分类也不自动成为峰中心定位真值。
3. **若无法取得合格输入**：保留此可复现性核实结果，暂不将 PeakBot 作为本数据上的原版正式对照。是否增加 centroid 适配或更换模型需要另定协议。

读取范围是全部原始 XML 元数据，不是 validation-only；没有读取标签或划分文件，没有解码强度数组、选择参数或计算测试指标。原 CNN 项目与历史结果未修改。
