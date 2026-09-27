# PeakBot 服务器下一步：数据与源码准入

更新日期：2026-09-27。

## 当前决定

不提交训练、GPU 推理或最终测试。PeakBot 作者 README 明确输入为 LC–HRMS profile-mode 数据；本地已完成完整 Zenodo ZIP 审计，51/51 文件保存为 MS:1000127 (`centroid spectrum`)，0 个 profile 文件，元数据完整性通过。服务器下一步复核同一输入身份及结论。vendor filter string 中的 `p` 不覆盖存储谱的 CV 声明。

质心峰不能通过插值恢复成原始实测 profile 谱。若完整包均为 centroid，原版 PeakBot 在这份数据上的 benchmark 不能直接成立。可以后续用作者 profile 示例做原任务运行复现，或索取同批 profile/raw 文件；这两者都不能自动代替 Zenodo 标签验证。自行改造 centroid 前处理需要另立适配协议，不能称原版完整复现。

## 服务器固定根目录

```text
/public/home/lulingli/lht/peakcnn/external_benchmarks/peakbot_v1/PeakBot
```

官方代码在 `source/PeakBot`，示例和权重在 `source/PeakBot_Example`。它们是固定 commit 的子模块，不是本仓库直接跟踪的源码。已补上 `.gitmodules`，保留两个原 commit，不修改官方源代码。

## 先执行这些命令

以下检查只需 Python 3.7+ 标准库，可以在 base 环境运行，不依赖 TensorFlow、NumPy 或 CUDA。

```bash
cd /public/home/lulingli/lht/peakcnn/external_benchmarks/peakbot_v1/PeakBot
git pull --ff-only
git submodule update --init --recursive
python -m unittest discover -s tests -v
python scripts/preflight.py \
  --zip /public/home/lulingli/lht/peakcnn/deep-learning-peak-detection/zenodo_data/A_dataset_for_evaluation_of_peak_detection_methods_v3.zip \
  --out-dir results/00_preflight/zenodo_server_v1
```

若服务器 ZIP 不在上述已知路径，先用 `ls -lh` 确认实际位置再替换 `--zip`；不要复制整个数据包。也可用 `--mzml-dir <已有原始mzML目录>` 或 `--mzml <单文件>`，三种输入只能选一种。

如果子模块路径已有本地文件导致 checkout 拒绝覆盖，保留文件并贴出 `git status --short` 和 `git submodule status`；不要使用 `git clean`、强制 checkout 或删除目录来绕过。

## 检查范围与结果

`report.json` 记录：固定源 commit、源码是否干净、5 个作者权重 SHA256、每个 mzML 的哈希、MS1 profile/centroid 数量、RT 单位、扫描数量、时间单调性及 peak-picking 步骤。ZIP 模式直接流式读取，不解压、不修改原件、不解码强度数组。

完整 ZIP 的元数据检查覆盖全部样本，不宣称是 validation-only，也不宣称没有读取任何测试相关原始文件字节。它不读取标签或划分文件，不进行模型推理、参数选择或测试性能计算。

```bash
python -c 'import json; x=json.load(open("results/00_preflight/zenodo_server_v1/report.json")); print(json.dumps(x["summary"],indent=2)); print("repository_pass=",x["repository"]["passed"])'
```

- `PASS` / 退出码 0：源码权重身份、元数据和 profile 条件通过。仍需后续验证集映射与真实候选 smoke，不等于正式指标准入。
- `BLOCKED` / 退出码 2：如实保存科学/工程不兼容，不是脚本崩溃。查看 `blocking_reasons`，不要跳过检查强行跑指标。
- 其他异常：文件路径、损坏包或权限问题，应先排查。

脚本拒绝覆盖已有 `report.json`。需要重跑时使用 `zenodo_server_v2` 等新目录，保留前次记录。

## 未完成事项与限制

未安装服务器 PeakBot 深度学习环境，未生成真实候选，未训练或计算 F1/MAE。当前没有真实峰中心标签，不以 MZmine feature RT、自动最高点或预测框中点冒充独立真值。

还发现固定版本 `runPeakBot` 在存在 `gdProps` 时用预处理候选的 `gdrt/gdmz` 覆盖 CNN 的 center 输出。若以后具备合适 profile 数据，须记录这一官方后处理语义，不能把导出的坐标直接称为纯 CNN 回归峰位。
