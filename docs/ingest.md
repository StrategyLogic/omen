# 数据摄取

本文档阐述 Omen 的数据摄取工作目录与流程。

## 1 工作目录

- `data/ingest/sources/`：源文档（PDF/TXT/MD）
- `data/ingest/extracted/`：抽取文本
- `data/ingest/knowledge/`：结构化知识文档（`*.md`）
- `data/ingest/graph/`：图文件（`*.json`）

## 2 流程

1. 将源文档放入 `sources/`
2. 生成可用文本到 `extracted/`
3. 生成结构化知识文档到 `knowledge/`
4. 生成图文件到 `graph/`
5. 使用 `ingest-dry-run` 验证候选与断言审核状态

```bash
omen ingest-dry-run --scenario data/scenarios/ontology.json --text-file data/ingest/sources/sample.txt --build-assertions
```

输出：`output/ingest_candidates.json`

## 3 文件命名建议

- 源文档：`<topic>_<source>_<yyyymm>.pdf|txt|md`
- 抽取文本：`<stem>_p<start>-<end>.txt`（如涉及分页）
- 知识文档：`<stem>_knowledge.md`
- 图文件：`<stem>_graph.json`

命名保持可追踪、可复用、可批处理。

## 4 提取关注点

- `candidates`：候选实体
- `assertions`：断言候选
- `assertion_review_summary`：`pending/approved/rejected` 汇总
- `source_inventory`：当前工作区资产清单

建议优先检查：

1. `mapped_count / candidate_count` 的比例
2. `assertion_review_summary.rejected` 是否异常偏高
3. 候选中是否保留了来源位置信息（页码/跨度）

## 5 约束

- 默认工作在项目内部，不依赖外部路径
- 所有输入输出都应保留源追踪信息

不建议将中间产物写入 `output/`；`output/` 主要用于推演结果。

## 6 相关文档

- [快速开始](quick-start.md)
- [精度评估](precision.md)

## 7 Prompt 分层与配置

Spec 6 的摄取与分析 prompt 已迁移到 YAML，并按能力层分离：

- `config/prompts/prompts_base.yaml`：公开层（OPEN），用于构建与 `case analyze persona`
- `config/prompts/prompts_pro.yaml`：增强层（PRO），仅用于云端能力，不在 OSS 本地命令中暴露

运行时由 `src/omen/ingest/llm_ontology/prompt_registry.py` 完成命令到模板的映射，并从 YAML `prompt_meta` 读取版本信息，写入分析结果中的 `run_meta.prompt_version`。

约束：

1. 构建时与分析时都只读取模板，不在代码中硬编码提示词正文。
2. OPEN 命令不能依赖 PRO 模板。
3. 分析产物必须可追溯到模板版本（`<prompt_id>@<version>`）。
