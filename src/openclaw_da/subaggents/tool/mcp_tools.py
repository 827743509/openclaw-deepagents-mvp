from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from openclaw_da.config import Settings

logger = logging.getLogger(__name__)


def _parse_args(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [part for part in value.split() if part]

    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        raise ValueError("MCP 参数必须是 JSON 字符串列表或空格分隔的字符串。")
    return parsed





async def load_travel_mcp_tools(settings: Settings) -> list[Any]:
    """为出行子 Agent 加载高德地图和 12306 MCP 工具。"""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("未安装 langchain-mcp-adapters，已禁用出行 MCP 工具。")
        return []

    connections: dict[str, dict[str, Any]] = {
        "railway_12306": {
            "transport": "stdio",
            "command": settings.railway_12306_mcp_command,
            "args": _parse_args(settings.railway_12306_mcp_args),
        },
    }

    if settings.amap_maps_api_key:
        connections["amap_maps"] = {
            "transport": "stdio",
            "command": settings.amap_mcp_command,
            "args": _parse_args(settings.amap_mcp_args),
            "env": {
                "AMAP_MAPS_API_KEY": settings.amap_maps_api_key,
            },
        }
    else:
        logger.warning("未设置 AMAP_MAPS_API_KEY，已禁用高德地图 MCP 工具。")

    tools: list[Any] = []
    for name, connection in connections.items():
        try:
            client = MultiServerMCPClient({name: connection}, tool_name_prefix=True)
            tools.extend(await client.get_tools())
        except Exception:
            logger.exception("从 %s 加载 MCP 工具失败。", name)

    return tools
