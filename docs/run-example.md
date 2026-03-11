# Run Example

本文档提供 Omen 当前 MVP 的本地运行示例。

## Prerequisites

- Python 3.12
- `pip`
- A Python environment of your choice (for example `conda`)

## Install

在项目根目录执行：

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

如果你只需要运行项目而不需要测试工具，也可以使用：

```bash
python -m pip install -e .
```

## Run the Baseline Scenario

执行内置的 ontology 场景：

```bash
omen simulate --scenario data/scenarios/ontology.json
```

默认会保存到仓库根目录下的 `output/result.json`。

如需保留历史文件并避免覆盖，可加 `--incremental`，生成时间戳后缀文件（例如 `output/result_20260311_153000_123456.json`）。

```bash
omen simulate --scenario data/scenarios/ontology.json --incremental
```

## What You Will Get

当前 MVP 会输出一个 JSON 结果，包含：

- `run_id`: 本次运行的唯一标识
- `status`: 运行状态
- `outcome_class`: 结果分类（如 `replacement` / `convergence` / `coexistence`）
- `winner`: 当前规则下的获胜主体与用户边数量
- `top_drivers`: 关键驱动因素
- `snapshots`: 每个时间步的快照
- `final_competition_edges`: 最终形成的竞争边
- `explanation`: 关键分叉点、因果链和叙述性总结

## Generate Explanation from Saved Result

对于已保存的运行结果，可以单独生成（或重新生成）解释报告：

```bash
omen explain --input output/result.json
```

默认会保存到 `output/explanation.json`。


同样可加 `--incremental`：

```bash
omen explain --input output/result.json --incremental
```

## Counterfactual Compare

使用 CLI 运行基线与反事实变体并输出对比结果：

```bash
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}'
```

默认会保存到 `output/comparison.json`。


同样可加 `--incremental`：

```bash
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}' --incremental
```

输出会包含：

- `winner_changed`
- `baseline_outcome_class` / `variation_outcome_class`
- `deltas`（核心指标变化）
- `explanation`（变体结果解释）

## Example Workflow

一个最小工作流如下：

```bash
conda activate omen
cd /mnt/ssd/projects/opensource/omen
python -m pip install -e ".[dev]"
omen simulate --scenario data/scenarios/ontology.json
omen explain --input output/result.json
cat output/result.json
```

## Output File Hygiene

- 所有本地生成结果建议统一放在仓库根目录 `output/` 下。
- `output/` 已加入忽略配置，避免将本地运行结果提交到 Git 仓库。
- 默认文件名采用覆盖策略；需要保留多次运行结果时使用 `--incremental`。

## Run Tests

运行全部测试：

```bash
pytest -q
```

只运行基线集成测试：

```bash
pytest tests/integration/test_ontology_baseline.py -q
```

## Notes

- 当前实现是 Ontology Battle MVP 的第一阶段。
- 结果已经支持基础运行、结构化输出、counterfactual compare 和 explainability。
