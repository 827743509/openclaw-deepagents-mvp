from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from deepagents import create_deep_agent, GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.redis import RedisSaver
from langgraph.types import Command
from pydantic import BaseModel, Field

from openclaw_da.config import get_settings
from openclaw_da.schemas import ChatRequest, ExtractResult

from openclaw_da.tools import (
    list_recent_emails,
    create_email_draft,
    send_email,
    list_calendar_events,
    create_calendar_event,
    add_reminder,
    list_reminders,
    web_search,
)

load_dotenv()

SYSTEM_PROMPT = """\
【最高优先级输出规则】
你必须只输出最终答案，禁止输出任何过程性话术。
但这不限制你在内部调用工具。
绝对禁止输出以下类型内容：
- 正在为您查询
- 正在查询
- 正在搜索
- 我将为您
- 请稍等
- 我明白了
- 当前配置
- 无法调用工具
- 无法联网搜索

邮件相关任务必须委派给 email-assistant。
如果用户要求介绍人物、概念、技术：
直接给出介绍内容，不要说你正在查询。

如果没有联网搜索能力：
基于已有知识回答，不要告诉用户“无法联网搜索”。

回答第一句话必须直接进入正文。

错误示例：
正在为您查询主播大司马的相关信息……

正确示例：
大司马，本名韩金龙，是中国知名游戏主播，早期曾是英雄联盟职业选手，后来转型为游戏主播……

你是一个 OpenClaw-like 个人 AI 助手，名字叫 OpenClaw-DA。

你的职责：
- 像一个靠谱的个人助理一样处理邮件、日程、提醒、研究和任务规划。
- 对复杂任务先规划，再执行；需要时派发子代理。
- 对敏感动作必须谨慎：发送邮件、创建/修改日程、删除文件、访问隐私数据前要先说明影响，并等待审批。
- 输出要简洁、可执行，中文用户默认用中文回复。
- 不要伪造外部系统状态；如果工具只是本地 MVP 模拟，要明确说明。
- 只输出最终答案。
- 不要说“我明白了”。
- 不要解释你的内部配置。
- 不要提到 agent、subagent、tool、task、TAVILY_API_KEY、代理类型、无法调用某某工具。
- 如果无法联网搜索，只基于已有知识回答，不要把“无法联网搜索”作为回答开头。
- 不要输出思考过程、执行过程、工具调用过程。
- 回答要直接进入正文。
- 默认使用中文回复中文用户。
- 时间相关任务要写清楚绝对日期、时间和时区。
"""



def build_agent():
    settings = get_settings()

    workspace = settings.openclaw_workspace.resolve()
    data_dir = settings.openclaw_data_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    ttl_config = {
        "default_ttl": 60 * 24 * 7,  # 7 天，单位分钟
        "refresh_on_read": True,
    }
    # FilesystemBackend 让 deep agent 可以使用文件系统作为短期上下文、草稿、记忆和技能目录。
    # virtual_mode=True 表示 Agent 看到的是虚拟路径，比较适合本地开发。
    backend = FilesystemBackend(root_dir=str(Path(".").resolve()), virtual_mode=True)

    checkpointer_cm = RedisSaver.from_conn_string(settings.redis_url,ttl=ttl_config)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()

    tools = [
    ]

    subagents = [
        {
            "name": "email-assistant",
            "description": "Use for email triage, summarization, drafting replies, and deciding whether a message needs action.",
            "system_prompt": (
                "你是邮件助理。发送邮件前先创建草稿。"
            ),
            "tools": [list_recent_emails, create_email_draft, send_email],
            "skills": ["/data/skills/email_triage/"],
        },
        {
            "name": "calendar-assistant",
            "description": "Use for scheduling, listing events, creating local calendar events, and reminder planning.",
            "system_prompt": (
                "你是日程助理。处理时间时要确认日期、时区和持续时间。"
                "创建日程前必须把标题、开始、结束、地点复述给用户。"
            ),
            "tools": [list_calendar_events, create_calendar_event, add_reminder, list_reminders],
            "skills": ["/data/skills/calendar_ops/"],
        },
        # {
        #     "name": "research-assistant",
        #     "description": "Use for web research, fact checking, and collecting sources before answering.",
        #     "system_prompt": (
        #         "你是研究助理。遇到需要新信息的问题，先搜索，再总结。"
        #         "结果要区分事实、推断和不确定点。"
        #     ),
        #     "tools": [web_search],
        # },
    ]
    llm = ChatOpenAI(
        model=settings.openclaw_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )

    register_harness_profile(
        "openai",
        HarnessProfile(
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        backend=backend,
        skills=[
        ],
        memory=["/data/memories/AGENTS.md"],
        subagents=subagents,
        interrupt_on={
            "send_email": {"allowed_decisions": ["approve", "reject"]},
            "create_calendar_event": {"allowed_decisions": ["approve", "edit", "reject"]},
            "write_file": True,
            "edit_file": True,
        },
        checkpointer=checkpointer,
        response_format=ExtractResult,
        name="openclaw-da",
    )
    return agent


def invoke_agent(req: ChatRequest, thread_id: str = "default") -> ExtractResult:
    agent = build_agent()
    if(req.decisions):
        return agent.invoke(
            Command(
                resume={
                    "decisions": req.decisions
                }
            ),
            config={"configurable": {"thread_id": thread_id}},
            version="v2",
        )["structured_response"]
    else:
       result=agent.invoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={"configurable": {"thread_id": thread_id}},
     )
       if(result["__interrupt__"]):
         return ExtractResult(message="",interrupt=True)
       else:
         return result["structured_response"];
def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def _format_human_interrupt(interrupts: Any) -> str | None:
    if not interrupts:
        return None

    if not isinstance(interrupts, (list, tuple)):
        interrupts = [interrupts]

    lines = ["Human review required."]
    for index, interrupt in enumerate(interrupts, start=1):
        value = getattr(interrupt, "value", interrupt)
        interrupt_id = getattr(interrupt, "id", None)
        if isinstance(value, dict):
            action_requests = value.get("action_requests") or []
            review_configs = value.get("review_configs") or []

            if action_requests:
                for action_index, action_request in enumerate(action_requests, start=1):
                    name = action_request.get("name", "unknown_action")
                    description = action_request.get("description")
                    args = action_request.get("args", {})
                    review_config = next(
                        (
                            config
                            for config in review_configs
                            if config.get("action_name") == name
                        ),
                        review_configs[action_index - 1]
                        if action_index - 1 < len(review_configs)
                        else {},
                    )
                    decisions = review_config.get("allowed_decisions", [])

                    lines.append(f"{index}.{action_index} Action: {name}")
                    if description:
                        lines.append(f"Description: {description}")
                    lines.append(f"Args: {_format_value(args)}")
                    if decisions:
                        lines.append(f"Allowed decisions: {', '.join(decisions)}")
                    if interrupt_id:
                        lines.append(f"Interrupt id: {interrupt_id}")
                continue

        lines.append(f"{index}. {_format_value(value)}")
        if interrupt_id:
            lines.append(f"Interrupt id: {interrupt_id}")

    return "\n".join(lines)



def extract_result(result: Any) -> ExtractResult:
    """Best-effort extraction for LangGraph/Deep Agents message output."""
    if isinstance(result, dict) and result.get("__interrupt__"):
        return ExtractResult(message="", interrupt=True)

    if isinstance(result, dict) and "messages" in result:
        messages = result["messages"]
        if messages:
            last = messages[-1]
            content = getattr(last, "content", None)
            if content is None and isinstance(last, dict):
                content = last.get("content")
            return ExtractResult(message=str(content))

