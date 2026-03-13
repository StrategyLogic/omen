# 推演精度评估指南

本文档说明如何评估推演结果的精度与可用性。

## 1 目标

精度评估回答三个问题：

- 结果是否稳定（重复运行一致性）
- 方向是否合理（条件变化后的方向正确性）
- 解释是否完整（条件→规则→证据链是否闭合）

## 2 核心指标

### 重复性

- `outcome_consistency`
- `top_driver_consistency`

### 方向正确性

- `directional_correctness`

### 解释完整性

- `trace_completeness`

## 3 最小操作流程

### 步骤 A：生成重复性评估

```bash
omen precision-eval --scenario data/scenarios/ontology.json --runs 5 --seed 42
```

输出：`output/precision.json`

### 步骤 B：运行一个反事实对比

```bash
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}'
```

输出：`output/comparison.json`

### 步骤 C：执行精度门禁

```bash
omen precision-gate --profile-json path/to/profile.json --precision-json output/precision.json --comparison-json output/comparison.json
```

输出：`output/precision_gate_report.json`

## 4 门禁解释

门禁报告会给出：

- 每项门禁的观测值与阈值
- 是否通过
- 未通过时的修复目标

## 5 Profile 模板

可使用如下模板创建 `profile.json`：

```json
{
	"profile_id": "p-ontology",
	"case_id": "ontology",
	"repeatability_threshold": 0.9,
	"directional_correctness_threshold": 0.85,
	"trace_completeness_threshold": 0.95,
	"status": "active"
}
```

## 6 阈值调参建议

- 初次落地可先用宽松阈值（例如 0.8 / 0.8 / 0.9）
- 稳定后逐步提高阈值，避免一次性过严导致无法迭代
- 任何阈值调整都应配套记录基线数据与调整原因

## 7 相关文档

- [快速开始](quick-start.md) 
- [战略本体](ontology.md) 
- [数据摄取](ingest.md)