from __future__ import annotations

import argparse
from uuid import uuid4

from openclaw_da.agent import invoke_agent, extract_result


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenClaw-like Deep Agents MVP")
    parser.add_argument("message", nargs="*", help="User message")
    parser.add_argument("--thread-id", default=None, help="Conversation thread id")
    args = parser.parse_args()

    thread_id = args.thread_id or f"cli-{uuid4().hex[:8]}"

    if args.message:
        message = " ".join(args.message)
        result = invoke_agent(message, thread_id=thread_id)
        print(extract_result(result).message)
        return

    print("OpenClaw-DA interactive mode. 输入 exit 退出。")
    print(f"thread_id={thread_id}")
    while True:
        message = input("\n你> ").strip()
        if message.lower() in {"exit", "quit", "q"}:
            break
        if not message:
            continue
        result = invoke_agent(message, thread_id=thread_id)
        print("\nAgent>")
        print(extract_text(result))


if __name__ == "__main__":
    main()
