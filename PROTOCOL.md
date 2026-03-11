# Omen Project Protocol

本文件定义 Omen 开源项目的边界与输出语义。

## 1. Identity

- Project: **Omen（爻）**
- Slogan: **Simulate the Signs. Reveal the Chaos.**
- Mission: 通过战略推演显现“征兆（signs）”，帮助用户理解未来可能的分叉路径。

## 2. Output Contract

Omen 的输出是“现象与路径”，不是“确定性结论”。

Omen MUST:

- 输出条件化路径（what may happen under conditions）
- 输出关键驱动因子与分叉点
- 提供可回放、可解释的推演结果

Omen MUST NOT:

- 声称提供确定性预测
- 代替用户做最终商业决策
- 将结果包装为保证命中的“答案”

## 3. Boundary

Omen 对外只定义自身边界，不承载外部服务叙事。

1. Omen 保持开源项目的独立性与社区属性。
2. Omen 的公开文档应聚焦项目能力与边界，不包含本地开发方式与内部运营细节。

## 4. Scope Contract (Open Source)

Omen 开源范围聚焦：

- 场景建模（scenario）
- 能力空间建模（capability space）
- 战略主体与动作空间（agents/actions）
- 推演执行与解释（simulation/explainability）

不在当前开源范围内：

- 面向客户的定制服务流程
- 商业交付模板与咨询方法库
- 企业内部专有策略资产

## 5. Documentation Contract

对外文档（README/docs/cases）必须满足：

1. 明确 Omen 的项目边界。
2. 可以展示项目全貌与核心概念。
3. 不包含本地环境名称、环境工具、开发工具与本地开发方式。
4. 当 `README.md` 更新时，必须同步更新 `README.zh.md`；该双语同步要求仅适用于 README。

本地开发与工具链信息应仅记录在本地文档（如 `.local.md`）。

## 6. Naming and Case Protocol

- Case 文件必须使用场景名命名，例如 `ontology.md`。
- 禁止使用 `case.md`、`demo.md` 这类泛名。
- 每个 case 必须定义：问题、主体、能力维度、动力机制、输出要求。

## 7. Decision Authority

Omen 的职责是“显现可能性”，最终决策权始终属于使用者。

> Omen shows the signs. Humans decide the future.
