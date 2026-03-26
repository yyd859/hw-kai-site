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

目标：把用户的硬件想法逐步收敛成可落地的方案。主线必须遵守：
Phase 1 = idea shaping
Phase 2 = abstract BOM formation
Phase 3 = late library resolution
Phase 4 = gap handling or build

你的职责：决定下一步要对用户说什么，以及 runtime 是否需要做后置 resolution / inspect / build。

核心原则：
1. 你只输出 JSON，不输出解释。
2. 前半段优先理解“用户想做什么”，不要一上来被现有 library 牵着走。
3. 先形成 commitment：project_brief / subsystems / abstract_bom / constraints / open_questions / selected_direction。
4. 只有当 selected_direction 已基本明确，并且 abstract_bom 已经成型后，才允许调用 library.search 做 late resolution。
5. library.search 在 planner 语义里表示“把 abstract BOM 里的角色映射到现有库组件”，不是早期探索工具。
6. library.inspect 只在需要确认某个已候选组件细节时使用。
7. build.generate 不是普通 tool call。只有当 resolved_components 足够、unresolved_roles 可接受、且用户明确要生成方案时，才把 next.type 设为 build。
8. 如果 resolution 发现缺件，不要把 missing 当作早期终点。优先进入 gap handling：告诉用户哪些角色已能落地、哪些角色还没 resolve、可选路径（降级 MVP / 替代方案 / 先补库）。
9. 只有真的完全无法继续时，才用 next.type=fail。
10. speak 是最终对用户说的话，简洁、自然、中文，呈现的是“当前承诺/下一步建议”，不是生硬的库搜索结果。

runtime tools：library.search, library.inspect。

输出格式：
{
  "speak": "给用户的话",
  "commitment": {
    "project_brief": "一句话理解",
    "requirements": ["..."],
    "constraints": ["..."],
    "subsystems": ["..."],
    "abstract_bom": [
      {"role": "input/button", "capability": "button", "notes": "用户按下时触发"}
    ],
    "open_questions": ["..."],
    "selected_direction": "先做可验证 MVP"
  },
  "memory_patch": {
    "project_brief": "...",
    "requirements": ["..."],
    "constraints": ["..."],
    "subsystems": ["..."],
    "abstract_bom": [{"role": "...", "capability": "...", "notes": "..."}],
    "open_questions": ["..."],
    "selected_direction": "...",
    "resolved_components": [
      {"role": "input/button", "module_id": "push_button", "label": "Push Button"}
    ],
    "unresolved_roles": ["camera_vision"],
    "gap_analysis": {
      "resolved": ["input/button -> push_button"],
      "unresolved": ["camera_vision"],
      "suggestions": ["先降级成按钮触发版", "改成非视觉传感方案", "后续补库"]
    },
    "selected_module_ids": ["push_button"],
    "selected_board_id": "esp32_devkit_v1",
    "ready_to_build": false
  },
  "next": {
    "type": "continue|tool|confirm|build|fail",
    "calls": [
      {"tool": "library.search", "arguments": {"query": "...", "capabilities": ["..."], "roles": [{"role": "...", "capability": "..."}] }},
      {"tool": "library.inspect", "arguments": {"id": "..."}}
    ],
    "build_context": {
      "project_brief": "...",
      "requirements": ["..."],
      "constraints": ["..."],
      "subsystems": ["..."],
      "abstract_bom": [{"role": "...", "capability": "..."}],
      "selected_direction": "...",
      "resolved_components": [{"role": "...", "module_id": "..."}],
      "selected_module_ids": ["..."],
      "selected_board_id": "esp32_devkit_v1"
    },
    "error_type": "missing_components|llm_unavailable|generation_not_supported_yet",
    "missing_components": ["..."]
  }
}

硬规则：
- next.type=continue：不调用工具；只问最关键的一个问题，或给出当前 abstract BOM / 方向供用户确认。
- next.type=tool：calls 至少 1 个；若包含 library.search，必须已经有 selected_direction + abstract_bom。
- next.type=confirm：表示方案基本收敛，可请用户确认是否开始生成。
- next.type=build：build_context 必填；通常应包含 resolved_components 或 selected_module_ids。
- next.type=fail：只用于完全无法继续的情况，不要把普通缺件分析直接做成 fail。
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


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _normalize_abstract_bom(value: Any) -> list[dict[str, Any]]:
    items = value if isinstance(value, list) else []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if isinstance(item, dict):
            role = str(item.get("role") or item.get("name") or "").strip()
            capability = str(item.get("capability") or item.get("type") or "").strip()
            notes = str(item.get("notes") or item.get("description") or "").strip()
            if role or capability or notes:
                normalized.append({"role": role, "capability": capability, "notes": notes})
        elif isinstance(item, str) and item.strip():
            normalized.append({"role": item.strip(), "capability": "", "notes": ""})
    return normalized


def _normalize_resolved_components(value: Any) -> list[dict[str, Any]]:
    items = value if isinstance(value, list) else []
    normalized: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        module_id = str(item.get("module_id") or item.get("id") or "").strip()
        role = str(item.get("role") or item.get("capability") or "").strip()
        label = str(item.get("label") or "").strip()
        capability = str(item.get("capability") or "").strip()
        if module_id or role:
            normalized.append(
                {
                    "role": role,
                    "module_id": module_id,
                    "label": label,
                    "capability": capability,
                }
            )
    return normalized


def _merged_runtime_view(session_memory: dict[str, Any], envelope: dict[str, Any]) -> dict[str, Any]:
    memory_patch = envelope.get("memory_patch") or {}
    commitment = envelope.get("commitment") or {}
    return {
        **(session_memory or {}),
        **commitment,
        **memory_patch,
    }


def _resolution_ready(runtime_view: dict[str, Any]) -> bool:
    selected_direction = str(runtime_view.get("selected_direction") or "").strip()
    abstract_bom = _normalize_abstract_bom(runtime_view.get("abstract_bom"))
    return bool(selected_direction and abstract_bom)


def _default_continue_speak(runtime_view: dict[str, Any], latest_user_message: str | None) -> str:
    if runtime_view.get("abstract_bom"):
        return "我先按这个方向收敛成一版抽象方案：如果没偏，我再往可落地模块上做映射。"
    if latest_user_message:
        return "我先不急着查库，先把你想做的核心效果和最小可验证版本收敛一下。"
    return "我先把方案抽象成模块角色，再决定要不要做库内映射。"


def _sanitize_envelope(envelope: dict[str, Any], session_memory: dict[str, Any], latest_user_message: str | None) -> dict[str, Any]:
    if not isinstance(envelope, dict):
        envelope = {}

    envelope.setdefault("speak", "")
    envelope.setdefault("commitment", {})
    envelope.setdefault("memory_patch", {})
    envelope.setdefault("next", {"type": "continue"})

    commitment = envelope["commitment"] if isinstance(envelope["commitment"], dict) else {}
    memory_patch = envelope["memory_patch"] if isinstance(envelope["memory_patch"], dict) else {}
    next_step = envelope["next"] if isinstance(envelope["next"], dict) else {"type": "continue"}

    for container in (commitment, memory_patch):
        container["requirements"] = _normalize_string_list(container.get("requirements"))
        container["constraints"] = _normalize_string_list(container.get("constraints"))
        container["subsystems"] = _normalize_string_list(container.get("subsystems"))
        container["open_questions"] = _normalize_string_list(container.get("open_questions"))
        container["unresolved_roles"] = _normalize_string_list(container.get("unresolved_roles"))
        container["selected_module_ids"] = _normalize_string_list(container.get("selected_module_ids"))
        container["abstract_bom"] = _normalize_abstract_bom(container.get("abstract_bom"))
        container["resolved_components"] = _normalize_resolved_components(container.get("resolved_components"))
        if not isinstance(container.get("gap_analysis"), dict):
            container["gap_analysis"] = {}

    next_step.setdefault("type", "continue")
    next_step.setdefault("calls", [])
    next_step.setdefault("build_context", {})

    runtime_view = _merged_runtime_view(session_memory, {"commitment": commitment, "memory_patch": memory_patch})

    if not memory_patch.get("project_brief") and latest_user_message:
        memory_patch["project_brief"] = str(runtime_view.get("project_brief") or latest_user_message).strip()

    calls = next_step.get("calls") if isinstance(next_step.get("calls"), list) else []
    if next_step.get("type") == "tool":
        wants_resolution = any(isinstance(call, dict) and call.get("tool") == "library.search" for call in calls)
        if wants_resolution and not _resolution_ready(runtime_view):
            next_step = {"type": "continue"}
            if not envelope["speak"]:
                envelope["speak"] = _default_continue_speak(runtime_view, latest_user_message)

    if next_step.get("type") == "fail" and next_step.get("error_type") == "missing_components" and runtime_view.get("abstract_bom"):
        next_step = {
            "type": "continue",
            "missing_components": next_step.get("missing_components", []),
        }
        if not envelope["speak"]:
            envelope["speak"] = "我已经先收敛出了抽象方案，下一步会把缺口整理成可选路径，而不是直接卡死。"

    envelope["commitment"] = commitment
    envelope["memory_patch"] = memory_patch
    envelope["next"] = next_step
    return envelope


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
    return _sanitize_envelope(envelope, session_memory, user_message)
