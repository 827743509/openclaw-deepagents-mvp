# map_agent.py

import os
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient

from .tool.mcp_tools import load_travel_mcp_tools
from ..config import get_settings
async def build_map_agent():
    settings = get_settings()

    amap_tools = await load_travel_mcp_tools

    llm = ChatOpenAI(
        model=settings.openclaw_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )

    return create_agent(
        model=llm,
        tools=amap_tools,
        system_prompt="你是地图助手，负责地址解析、路线规划、地点查询、逆地理编码等任务。",
    )
