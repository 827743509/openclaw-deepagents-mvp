# 仓库指南

## 项目结构与模块组织

本仓库是一个基于 LangChain Deep Agents 的 OpenClaw-like 个人助理 MVP。

- `src/openclaw_da/agent.py`：主 Agent 编排、子 Agent 注册、人工打断和结构化返回。
- `src/openclaw_da/server.py`：FastAPI HTTP 服务入口。
- `src/openclaw_da/cli.py`：命令行入口。
- `src/openclaw_da/config.py`：基于环境变量的配置。
- `src/openclaw_da/tools/`：邮件、日程、提醒、搜索等本地工具。
- `src/openclaw_da/mcp_tools.py`：外部 MCP 工具加载逻辑。
- `data/skills/`：Agent 可加载的技能说明。
- `data/memories/`：长期记忆文件。
- `workspace/`、`drafts/`：运行时输出目录，避免提交生成的个人数据。

当前没有 `tests/` 目录；修改行为逻辑时请新增对应测试。

## 构建、测试与本地运行

创建并安装本地环境：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

运行 CLI：

```powershell
python -m openclaw_da.cli
```

启动 HTTP API：

```powershell
uvicorn openclaw_da.server:app --reload --port 8000
```

轻量语法检查：

```powershell
python -m py_compile src\openclaw_da\agent.py
```

## 代码风格与命名约定

使用 Python 3.11+ 语法，遵循 PEP 8：4 空格缩进，函数和变量使用 `snake_case`，Pydantic 模型使用 `PascalCase`。工具函数应保持小而明确，按领域放在 `src/openclaw_da/tools/` 下；类似 MCP 客户端加载的集成逻辑可以独立成模块。

新增配置优先写入 `config.py`，不要在业务逻辑中直接读取环境变量。面向用户的 Agent 提示词默认使用中文，保持简洁、可执行。注释也使用中文。打印的日志信息也使用中文。


## 提交与 PR 规范

当前 Git 历史使用简短中文提交信息，例如 `第一次提交`、`细节调整`。继续使用简洁、祈使式描述，例如 `添加出行子 agent`、`修复打断提示返回`。

PR 应包含变更摘要、影响模块、手动验证命令，以及新增或变更的 `.env` 配置。有关联 issue 时请链接。只有 UI 相关变更需要截图。

## 安全与配置提示

不要提交 `.env`、API Key、SMTP 密码或生成的个人数据。发送邮件、创建日程等敏感动作应保留审批或显式配置开关。新增环境变量时，在 PR 说明中写清用途，并在 `config.py` 中提供安全默认值。
