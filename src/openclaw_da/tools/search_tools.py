from __future__ import annotations

from typing import Literal
from langchain_core.tools import tool

from openclaw_da.config import get_settings


@tool
def web_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
) -> str:
    """Search the web using Tavily if TAVILY_API_KEY is configured."""
    settings = get_settings()
    if not settings.tavily_api_key:
        return "TAVILY_API_KEY is not configured. Cannot search the web."

    from tavily import TavilyClient

    client = TavilyClient(api_key=settings.tavily_api_key)
    result = client.search(query=query, max_results=max_results, topic=topic)
    items = result.get("results", [])
    if not items:
        return "No search results."

    return "\n\n".join(
        f"Title: {item.get('title')}\nURL: {item.get('url')}\nContent: {item.get('content')}"
        for item in items
    )
