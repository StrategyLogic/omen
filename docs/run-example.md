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

如果希望将结果写入文件：

```bash
omen simulate --scenario data/scenarios/ontology.json --output result.json
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

## Example Workflow

一个最小工作流如下：

```bash
conda activate omen
cd /mnt/ssd/projects/opensource/omen
python -m pip install -e ".[dev]"
omen simulate --scenario data/scenarios/ontology.json --output result.json
cat result.json
```

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
- 结果已经支持基础运行、结构化输出与测试验证。
- 后续会继续补充 replay、counterfactual compare 和 explainability 相关能力。
