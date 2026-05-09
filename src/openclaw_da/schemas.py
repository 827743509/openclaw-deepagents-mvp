from typing import Dict, Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None
    decisions:list[dict[str, Any]] | None = None

class ExtractResult(BaseModel):
    message: str = Field(default="", description="最终结果")
    interrupt: bool = Field(default=False, description="是否被打断")
    action: str | None = Field(default=None, description="动作类型")
    data: dict[str, Any] | None = Field(default=None, description="附加数据")