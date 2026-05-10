from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from deepagents import create_deep_agent, GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile, \
    FilesystemMiddleware
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

SYSTEM_PROMPT = """
你是 OpenClaw 的主控调度 Agent。
你负责分析用户请求、规划步骤、分配给子 agent，并最终汇总结果。
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


    # 1. 注册一个精简 profile
    register_harness_profile(
        "openai:"+settings.openclaw_model,
        HarnessProfile(
            # 替换 DeepAgents 默认基础系统提示词
            base_system_prompt="""
    你是一个主控规划 Agent，负责拆解任务、制定计划、分发子任务并汇总结果。

    你只能做三类事情：
    1. 使用 write_todos 维护任务计划；
    2. 使用 task 把子任务分发给合适的子 agent；
    3. 根据子 agent 返回的结果，汇总成最终答案。
    
    最终回复时，必须使用 ExtractResult 结构化输出，不要只返回普通文本。
    
    规则：
    - 复杂任务必须先规划，再分发。
    - 不要自己执行专业任务，优先交给对应子 agent。
    - 不要读写文件。
    - 不要使用命令行。
    - 子 agent 返回结果后，你负责判断是否还需要继续分发或汇总。
    """,

            # 隐藏文件/沙箱相关工具
            excluded_tools=frozenset({
                "ls",
                "read_file",
                "write_file",
                "edit_file",
                "execute",
                "glob",
                "grep",
            }),

            # 关闭默认 general-purpose 子 agent
            # 只保留你自己定义的子 agent
            general_purpose_subagent=GeneralPurposeSubagentProfile(
                enabled=False
            ),
        ),
    )

    agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        skills=[
        ],
        subagents=subagents,
        interrupt_on={
            "send_email": {"allowed_decisions": ["approve", "reject"]},
            "create_calendar_event": {"allowed_decisions": ["approve", "edit", "reject"]}
        },
        checkpointer=checkpointer,
        response_format=ExtractResult,
        name="openclaw-da",
    )
    return agent


def invoke_agent(req: ChatRequest, thread_id: str = "default") -> ExtractResult:
    agent = build_agent()
    if(req.decisions):
        result=agent.invoke(
            Command(
                resume={
                    "decisions": req.decisions
                }
            ),
            config={"configurable": {"thread_id": thread_id}},
            version="v2",
        )
        return result["structured_response"]
    else:
       result=agent.invoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={"configurable": {"thread_id": thread_id},},version="v2"
     )
       if result.interrupts:
         return ExtractResult(
             message="需要人工确认后继续。",
             interrupt=True,
         )
       else:
         return result["structured_response"];
def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)



