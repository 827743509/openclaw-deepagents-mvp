from __future__ import annotations

import argparse
from uuid import uuid4

from openclaw_da.agent import invoke_agent
from openclaw_da.schemas import ChatRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw 风格的 Deep Agents 个人助理 MVP")
    parser.add_argument("message", nargs="*", help="用户消息")
    parser.add_argument("--thread-id", default=None, help="会话线程 ID")
    args = parser.parse_args()

    thread_id = args.thread_id or f"cli-{uuid4().hex[:8]}"

    if args.message:
        message = " ".join(args.message)
        result = invoke_agent(ChatRequest(message=message), thread_id=thread_id)
        print(result.message)
        return

    print("OpenClaw-DA 交互模式。输入 exit 退出。")
    print(f"thread_id={thread_id}")
    while True:
        message = input("\n你> ").strip()
        if message.lower() in {"exit", "quit", "q"}:
            break
        if not message:
            continue
        result = invoke_agent(ChatRequest(message=message), thread_id=thread_id)
        print("\n助手>")
        print(result.message)


if __name__ == "__main__":
    main()
