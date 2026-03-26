from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class LLMUnavailableError(Exception):
    pass


SYSTEM_PROMPT = """你是 HW-KAI 的 mvp0.2 runtime planner。

目标：用 free-form planning 驱动硬件项目对话。你负责决定下一步要说什么，以及 runtime 要不要查库、看模块、或者生成 build。

原则：
1. 你只输出 JSON，不输出解释。
2. 你不暴露思考过程，只暴露 commitment（当前承诺/理解）。
3. 对话层数不固定；如果信息不够，就继续问。
4. 优先使用 runtime tools 获取真实 library 信息，不要编造库里没有的模块。
5. runtime tools 只有：library.search, library.inspect。
6. build.generate 不是普通 tool call。只有当你非常确定库里足够、并且用户明确要生成方案时，才把 next.type 设为 build。
7. 如果缺件或能力不在库里，诚实失败，next.type=fail，并给 error_type=missing_components。
8. 如果用户只是探索方案，不要急着 build。
9. speak 是最终要对用户说的话，简洁、自然、中文。

输出格式：
{
  "speak": "给用户的话",
  "commitment": {
    "project_brief": "一句话理解",
    "requirements": ["..."],
    "constraints": ["..."]
  },
  "memory_patch": {
    "project_brief": "...",
    "requirements": ["..."],
    "constraints": ["..."],
    "selected_module_ids": ["..."],
    "selected_board_id": "esp32_devkit_v1",
    "ready_to_build": false
  },
  "next": {
    "type": "continue|tool|confirm|build|fail",
    "calls": [
      {"tool": "library.search", "arguments": {"query": "...", "capabilities": ["..."]}},
      {"tool": "library.inspect", "arguments": {"id": "..."}}
    ],
    "build_context": {
      "project_brief": "...",
      "requirements": ["..."],
      "constraints": ["..."],
      "selected_module_ids": ["..."],
      "selected_board_id": "esp32_devkit_v1"
    },
    "error_type": "missing_components|llm_unavailable|generation_not_supported_yet",
    "missing_components": ["..."]
  }
}

要求：
- next.type=tool 时，calls 至少 1 个。
- next.type=build 时，build_context 必填，且 speak 应说明即将生成或已经可以生成。
- next.type=confirm 时，speak 应明确询问用户是否按当前理解生成。
- next.type=continue 时，不调用工具，继续问最关键的一个问题。
- next.type=fail 时，speak 要诚实解释问题。
"""


def _get_llm_config() -> dict[str, str]:
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if deepseek_key and deepseek_key not in ("", "placeholder"):
        return {
            "provider": "deepseek",
            "api_key": deepseek_key,
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
            "model": os.getenv("MODEL_NAME", "deepseek-chat"),
        }

    if openai_key and openai_key not in ("", "placeholder"):
        return {
            "provider": "openai",
            "api_key": openai_key,
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            "model": os.getenv("MODEL_NAME", "gpt-4o-mini"),
        }

    raise LLMUnavailableError("No LLM API key configured")


def _build_client(config: dict[str, str]) -> AsyncOpenAI:
    base_url = config["base_url"]
    if config["provider"] == "deepseek" and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return AsyncOpenAI(api_key=config["api_key"], base_url=base_url)


def _parse_json(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


async def plan_next_step(session_memory: dict[str, Any], history: list[dict[str, Any]], user_message: str | None, tool_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    config = _get_llm_config()
    client = _build_client(config)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": json.dumps(
                {
                    "session_memory": session_memory,
                    "recent_history": history[-12:],
                    "latest_user_message": user_message,
                    "tool_results": tool_results or [],
                },
                ensure_ascii=False,
            ),
        },
    ]

    resp = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    envelope = _parse_json(raw)
    envelope.setdefault("speak", "")
    envelope.setdefault("commitment", {})
    envelope.setdefault("memory_patch", {})
    envelope.setdefault("next", {"type": "continue"})
    envelope["next"].setdefault("type", "continue")
    return envelope
