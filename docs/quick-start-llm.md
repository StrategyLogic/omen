
# 快速开始：使用 LLM 生成

Omen `0.2.0` 版本起开始集成大语言模型增强生成。本文档说明如何配置大模型，通过 `Strategic Actor` CLI 示例生成产出物、完成结果检查。

## 1. 准备运行

下载 Omen 源代码：

```bash
git clone git@github.com:StrategyLogic/omen.git
cd omen
```

在仓库根目录下执行以下命令，安装项目依赖：

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

### 配置 LLM

先复制模板：

```bash
cp config/llm.example.toml config/llm.toml
```

然后编辑 `config/llm.toml`，填入你要使用的模型配置（如 provider、model、api_key 环境变量名等）。

如你的配置依赖环境变量，请在 `.env` 中设置对应密钥。

## 2. 准备输入文档

将案例文档放在 `cases/actors/`，例如：`cases/actors/x-developer.md`

命令中的 `--doc x-developer` 会解析到上述文件。

### 运行 CLI 生成

```bash
omen analyze actor --doc x-developer --config config/llm.toml
```

默认输出目录：

- `output/actors/x-developer/`

## 3. 检查生成结果

先检查目录与文件是否存在：

```bash
ls -lah output/actors/x-developer/
```

期望至少包含：

- `strategy_ontology.json`
- `actor_ontology.json`
- `analyze_status.json`
- `analyze_persona.json`
- `generation.json`

再执行结构校验：

```bash
omen validate actor --doc x-developer --output-dir output/actors
```

判定标准：

- 输出 `status=pass`：可进入后续 UI 展示或下游流程
- 输出 `status=fail`：根据 `errors` 字段逐项修复输入文档或配置后重试

## 4. 常见问题

- 命令找不到 `omen`：确认虚拟环境已激活，或使用 `python -m pip install -e .` 重新安装。
- LLM 调用失败：检查 `config/llm.toml` 与环境变量是否匹配。
- `--doc` 报文件不存在：确认 `cases/actors/<doc>.md` 文件名与命令参数一致。