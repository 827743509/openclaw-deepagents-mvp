from __future__ import annotations

from typing import Dict, Any
from uuid import uuid4
from fastapi import FastAPI
from pydantic import BaseModel, Field

from openclaw_da.agent import invoke_agent, extract_result
from openclaw_da.schemas import ChatRequest

app = FastAPI(title="OpenClaw Deep Agents MVP")





class ChatResponse(BaseModel):
    thread_id: str
    response: str
    interrupt: bool =Field(default=False, description="是否被打断")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    thread_id = req.thread_id or f"http-{uuid4().hex[:8]}"
    result = invoke_agent(req, thread_id=thread_id)
    return ChatResponse(thread_id=thread_id, response=result.message, interrupt=result.interrupt)
