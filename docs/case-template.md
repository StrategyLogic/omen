# Case Template

本模板用于定义 Omen 的展示场景（Show Case）。

## Naming Rule

案例文件必须直接使用场景名称命名，放在 `cases/` 目录下。

- 正确：`cases/ontology.md`
- 正确：`cases/vector-memory.md`
- 正确：`cases/open-models-vs-closed-apis.md`
- 错误：`cases/case.md`
- 错误：`cases/demo.md`

命名原则：

- 使用小写英文
- 使用场景主题名，而不是通用占位词
- 多词场景使用连字符连接
- 文件名应能在 README 的 Show Cases 中直接表达主题

## Structure

每个 case 建议包含以下章节。

### 1. Title

直接写场景名称，格式示例：

```md
# Ontology 战场：Database vs AI Memory
```

### 2. Case Summary

用 1-2 段说明这个 case 在推演什么，以及它为什么重要。

### 3. Why This Case Matters

解释该场景的行业背景、技术冲突和展示价值。

### 4. Strategic Question

明确本场景的核心战略问题。建议写成 1 个主问题 + 3 到 4 个子问题。

### 5. Agents

列出该场景中的主要主体，建议包含：

- 主体类型
- 目标
- 优势
- 典型动作

### 6. Capability Space

定义场景中的关键能力维度。建议列出 8-15 个维度。

### 7. Key Dynamics

说明该场景里的主要演化机制，例如：

- 能力替代
- 迁移摩擦
- 生态反馈
- 定价压力
- 联盟/并购
- 标准推进

### 8. Possible Outcomes

定义该场景可能出现的主要结果，一般建议 3 类：

- 替代
- 融合
- 长期共存

### 9. What Omen Should Output

说明跑完推演后，系统最少需要输出什么：

- 时间窗口
- 关键拐点
- 因果链条
- 关键变量
- 最优策略组合
- 反事实结果

### 10. Demo Value

解释这个场景作为公开展示案例，能够突出 Omen 的哪些能力。

### 11. Expected Expansion

列出可以沿同一主题继续扩展的相邻场景。

## Minimal Skeleton

```md
# [Case Title]

这是 Omen 的一个展示场景。

## Case Summary

[用 1-2 段说明场景定义。]

## Why This Case Matters

[说明行业背景与展示价值。]

## Strategic Question

> [写出核心战略问题]

## Agents

### 1. [Agent Type]
- [主体定义]
- [优势与限制]
- [典型动作]

## Capability Space

- [Capability A]
- [Capability B]
- [Capability C]

## Key Dynamics

### 1. [Dynamic A]
[说明机制]

## Possible Outcomes

### A. [Outcome A]
[说明结果]

## What Omen Should Output

- [Output A]
- [Output B]

## Demo Value

[说明公开展示价值]

## Expected Expansion

- [Adjacent Case A]
- [Adjacent Case B]
```

## Review Checklist

发布前请确认：

- 文件名符合命名规范
- 标题与文件名表达的是同一主题
- 场景问题足够具体，而不是泛泛描述行业趋势
- 智能体与能力维度可映射到推演模型
- 输出部分明确说明系统要给出哪些结果
- 文案是“直接陈述场景”，不展示内部推导过程
