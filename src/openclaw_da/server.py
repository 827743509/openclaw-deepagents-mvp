from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from openclaw_da.agent import close_agent, invoke_agent, build_agent
from openclaw_da.schemas import ChatRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = await build_agent()
    try:
        yield
    finally:
        close_agent()


app = FastAPI(lifespan=lifespan)


class ChatResponse(BaseModel):
    thread_id: str
    response: str
    interrupt: bool = Field(default=False, description="是否被打断")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    thread_id = req.thread_id or f"http-{uuid4().hex[:8]}"
    result = await invoke_agent(req, thread_id=thread_id)
    return ChatResponse(thread_id=thread_id, response=result.message, interrupt=result.interrupt)
