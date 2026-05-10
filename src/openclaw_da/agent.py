from __future__ import annotations

import json
from typing import Any

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    create_deep_agent,
    register_harness_profile,
)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.redis import RedisSaver
from langgraph.types import Command

from openclaw_da.config import get_settings
from openclaw_da.subaggents.tool.mcp_tools import load_travel_mcp_tools
from openclaw_da.schemas import ChatRequest, ExtractResult
from openclaw_da.tools import (
    create_email_draft,
    list_recent_emails,
    send_email,
)

load_dotenv()

SYSTEM_PROMPT = """
你是 OpenClaw 的主控调度 Agent。你负责分析用户请求、规划步骤、分配给子 Agent，并最终汇总结论。

工作要求：
- 面向用户的回复使用简洁中文。
- 涉及发送邮件、创建日程等敏感动作时，必须等待人工审批或明确配置允许。
- 最终回复必须符合 ExtractResult 结构化格式。
"""

_agent = None
_checkpointer_cm = None


async def build_agent():
    global _agent, _checkpointer_cm

    if _agent is not None:
        return _agent

    settings = get_settings()

    workspace = settings.openclaw_workspace.resolve()
    data_dir = settings.openclaw_data_dir.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    ttl_config = {
        "default_ttl": 60 * 24 * 7,  # 7 天，单位为分钟
        "refresh_on_read": True,
    }

    _checkpointer_cm = RedisSaver.from_conn_string(settings.redis_url, ttl=ttl_config)
    checkpointer = _checkpointer_cm.__enter__()
    checkpointer.setup()

    tools = []
    travel_tools =await load_travel_mcp_tools(settings)

    subagents = [
        {
            "name": "email-assistant",
            "description": "用于邮件分拣、摘要、回复草稿，以及判断邮件是否需要进一步处理。",
            "system_prompt": (
                "你是邮件助理。默认先创建邮件草稿；"
                "除非用户明确要求并且系统配置允许，否则不要直接发送邮件。"
            ),
            "tools": [list_recent_emails, create_email_draft, send_email],
            "skills": ["/data/skills/email_triage/"],
        },
        {
            "name": "travel-assistant",
            "description": (
                "用于中国出行规划、高德地图路线规划、地理编码、地点搜索、当前位置查询，"
                "以及 12306 火车票余票和车次查询。"
            ),
            "system_prompt": (
                "你是中国出行规划助理。"
                "需要路线规划、地理编码、距离、导航、地点或 POI 查询时，使用高德地图 MCP 工具。"
                "需要火车票余票、车次、站点、时刻表或票价查询时，使用 12306 MCP 工具。"
                "查询火车票前，要确认出发城市或车站、到达城市或车站、出行日期；"
                "如果席别、乘客类型、是否只看高铁动车等条件会影响结果，也要一并确认或说明默认假设。"
                "返回结果使用简洁中文，包含可选路线、耗时、费用或票价信息，并明确说明关键假设。"
            ),
            "tools": travel_tools,
        },
    ]

    llm = ChatOpenAI(
        model=settings.openclaw_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )

    # 注册一个精简 profile，限制主 Agent 只做规划、分派和汇总。
    register_harness_profile(
        "openai:" + settings.openclaw_model,
        HarnessProfile(
            # 替换 DeepAgents 默认基础系统提示词。
            base_system_prompt="""
    你是一个主控规划 Agent，负责拆解任务、制定计划、分发子任务并汇总结论。
    你只做三类事情：
    1. 使用 write_todos 维护任务计划；
    2. 使用 task 把子任务分发给合适的子 Agent；
    3. 根据子 Agent 返回的结果，汇总成最终答案。

    最终回复时，必须使用 ExtractResult 结构化输出，不要只返回普通文本。

    规则：
    - 复杂任务必须先规划，再分发。
    - 不要自己执行专业任务，优先交给对应子 Agent。
    - 不要读写文件。
    - 不要使用命令行。
    - 子 Agent 返回结果后，你负责判断是否还需要继续分发或汇总。
    """,
            # 隐藏文件和沙箱相关工具。
            excluded_tools=frozenset(
                {
                    "ls",
                    "read_file",
                    "write_file",
                    "edit_file",
                    "execute",
                    "glob",
                    "grep",
                }
            ),
            # 关闭默认 general-purpose 子 Agent，只保留显式定义的子 Agent。
            general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
        ),
    )

    _agent = create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        skills=[],
        subagents=subagents,
        interrupt_on={
            "send_email": {"allowed_decisions": ["approve", "reject"]},
            "create_calendar_event": {"allowed_decisions": ["approve", "edit", "reject"]},
        },
        checkpointer=checkpointer,
        response_format=ExtractResult,
        name="openclaw-da",
    )
    return _agent


async def invoke_agent(req: ChatRequest, thread_id: str = "default") -> ExtractResult:

    if req.decisions:
        result = await _agent.ainvoke(
            Command(
                resume={
                    "decisions": req.decisions,
                }
            ),
            config={"configurable": {"thread_id": thread_id}},
            version="v2",
        )
        return result["structured_response"]

    result = _agent.ainvoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    )
    if result.interrupts:
        return ExtractResult(
            message="需要人工确认后继续。",
            interrupt=True,
        )

    return result["structured_response"]


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return str(value)


def close_agent():
    global _checkpointer_cm

    if _checkpointer_cm is not None:
        _checkpointer_cm.__exit__(None, None, None)
        _checkpointer_cm = None
