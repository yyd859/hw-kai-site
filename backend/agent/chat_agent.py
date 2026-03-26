"""Multi-turn planning loop agent without mock fallback."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sessions: dict[str, dict[str, Any]] = {}

EMPTY_SPEC = {
    "object": None,
    "trigger": None,
    "needs_light": False,
    "needs_sound": False,
    "needs_display": False,
    "needs_sensor": False,
    "sensor_type": None,
    "needs_actuator": False,
    "actuator_type": None,
    "extra_notes": None,
}

SYSTEM_PROMPT = """你是一个硬件项目规划助手，负责通过多轮对话把用户需求整理成结构化 spec。

要求：
1. 只输出 JSON，不要输出任何解释文字。
2. 每轮先理解用户输入，再返回 updated_spec。
3. 如果信息不足，只问一个最关键的问题。
4. 如果信息已经足够，先给出中文摘要，等待用户确认。
5. 不要编造库里不存在的硬件；若用户提到高级能力（如摄像头识别、震动反馈），可以先记录到 extra_notes，但不要假装一定能实现。
6. spec 字段：
   - object: 这个装置是什么
   - trigger: button / auto / motion / remote / null
   - needs_light / needs_sound / needs_display / needs_sensor: 布尔值
   - sensor_type: temperature_humidity / soil_moisture / motion / null
   - needs_actuator: 是否需要执行器（例如继电器/水泵）
   - actuator_type: relay / pump / null
   - extra_notes: 额外需求，简短
7. 除非用户明确确认，否则 is_ready_for_final 设为 false。

严格输出：
{
  "assistant_message": "中文回复",
  "updated_spec": {
    "object": null,
    "trigger": null,
    "needs_light": false,
    "needs_sound": false,
    "needs_display": false,
    "needs_sensor": false,
    "sensor_type": null,
    "needs_actuator": false,
    "actuator_type": null,
    "extra_notes": null
  },
  "options": ["选项1", "选项2"],
  "is_ready_for_final": false
}
"""

CONFIRM_WORDS = {
    "确认", "可以", "就这样", "没问题", "好的", "好", "行", "可以了", "确认方案", "开始生成", "生成吧", "ok", "okay"
}

REVISE_HINTS = {
    "但是", "不过", "改", "修改", "不要", "换成", "改成", "再加", "还要", "希望", "最好", "另外"
}


class LLMUnavailableError(Exception):
    pass


def _get_llm_config() -> dict[str, str]:
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if deepseek_key and deepseek_key not in ("placeholder", ""):
        return {
            "provider": "deepseek",
            "api_key": deepseek_key,
            "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
            "model": os.getenv("MODEL_NAME", "deepseek-chat"),
        }

    if openai_key and openai_key not in ("placeholder", ""):
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


async def _llm_response(client: AsyncOpenAI, config: dict[str, str], history: list[dict[str, str]], spec: dict[str, Any], awaiting_confirmation: bool) -> dict[str, Any]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({
        "role": "system",
        "content": (
            f"当前已知 current_spec：{json.dumps(spec, ensure_ascii=False)}\n"
            f"是否正在等待确认：{json.dumps(awaiting_confirmation, ensure_ascii=False)}"
        ),
    })
    messages.extend(history)

    resp = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(raw)
    parsed.setdefault("updated_spec", spec)
    parsed.setdefault("options", [])
    parsed.setdefault("is_ready_for_final", False)
    return parsed


def _is_spec_ready(spec: dict[str, Any]) -> bool:
    has_object = bool(spec.get("object") or spec.get("trigger"))
    has_function = any([
        spec.get("needs_light"),
        spec.get("needs_sound"),
        spec.get("needs_display"),
        spec.get("needs_sensor"),
        spec.get("needs_actuator"),
    ])
    return has_object and has_function


def _is_confirm_message(message: str) -> bool:
    msg = message.strip().lower()
    if not msg:
        return False
    if any(hint in msg for hint in REVISE_HINTS):
        return False
    return any(word in msg for word in CONFIRM_WORDS)


def _build_confirmation_message(spec: dict[str, Any]) -> str:
    parts = []
    if spec.get("object"):
        parts.append(f"做一个“{spec['object']}”")

    trigger_map = {
        "button": "按钮触发",
        "auto": "自动运行",
        "motion": "感应触发",
        "remote": "遥控触发",
    }
    if spec.get("trigger"):
        parts.append(trigger_map.get(spec["trigger"], spec["trigger"]))

    features = []
    if spec.get("needs_light"):
        features.append("灯光")
    if spec.get("needs_sound"):
        features.append("声音")
    if spec.get("needs_display"):
        features.append("显示")
    if spec.get("needs_sensor"):
        sensor = spec.get("sensor_type") or "传感器"
        features.append(f"{sensor}检测")
    if spec.get("needs_actuator"):
        actuator = spec.get("actuator_type") or "执行器"
        features.append(actuator)

    feature_text = "、".join(features) if features else "基础功能"
    body = "，".join(parts) if parts else "这个硬件项目"
    extra = f"。补充：{spec['extra_notes']}" if spec.get("extra_notes") else ""
    return f"我目前理解的方案是：{body}，包含 {feature_text}{extra}。如果这样没问题，你回复“确认”我就进入最终生成；如果想改，我可以继续调整。"


def get_or_create_session(session_id: str) -> dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "current_spec": dict(EMPTY_SPEC),
            "turn": 0,
            "awaiting_confirmation": False,
            "last_intent_source": "llm",
        }
    return sessions[session_id]


def _merge_spec(current_spec: dict[str, Any], updated_spec: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current_spec)
    for key, value in updated_spec.items():
        if value is not None:
            merged[key] = value
    return merged


def _error_response(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "state": "error",
        "assistant_message": "AI 连接失败，请稍后再试。",
        "error_type": "llm_unavailable",
        "is_ready_for_final": False,
    }


async def process_message(session_id: str, message: str) -> dict[str, Any]:
    session = get_or_create_session(session_id)

    if session.get("awaiting_confirmation") and _is_confirm_message(message):
        session["history"].append({"role": "user", "content": message})
        session["awaiting_confirmation"] = False
        session["turn"] += 1
        return {
            "session_id": session_id,
            "state": "final",
            "assistant_message": f"最终确认如下：{_build_confirmation_message(session['current_spec']).replace('如果这样没问题，你回复“确认”我就进入最终生成；如果想改，我可以继续调整。', '')}",
            "current_spec": session["current_spec"],
            "options": [],
            "is_ready_for_final": True,
            "intent_source": session.get("last_intent_source", "llm"),
        }

    try:
        config = _get_llm_config()
        client = _build_client(config)
    except Exception:
        return _error_response(session_id)

    session["history"].append({"role": "user", "content": message})

    try:
        result = await _llm_response(
            client,
            config,
            session["history"],
            session["current_spec"],
            session.get("awaiting_confirmation", False),
        )
    except Exception:
        return _error_response(session_id)

    updated_spec = result.get("updated_spec", session["current_spec"])
    session["current_spec"] = _merge_spec(session["current_spec"], updated_spec)

    assistant_msg = result.get("assistant_message", "")
    options = result.get("options", [])
    ready_by_content = _is_spec_ready(session["current_spec"])

    if ready_by_content:
        session["awaiting_confirmation"] = True
        if not assistant_msg or result.get("is_ready_for_final"):
            assistant_msg = _build_confirmation_message(session["current_spec"])
        state = "confirming"
        is_ready_for_final = False
        if not options:
            options = ["确认，开始生成", "我想再改一下"]
    else:
        session["awaiting_confirmation"] = False
        state = "planning" if session["turn"] == 0 else "proposal"
        is_ready_for_final = False

    session["history"].append({"role": "assistant", "content": assistant_msg})
    session["turn"] += 1
    session["last_intent_source"] = "llm"

    return {
        "session_id": session_id,
        "state": state,
        "assistant_message": assistant_msg,
        "current_spec": session["current_spec"],
        "options": options,
        "is_ready_for_final": is_ready_for_final,
        "intent_source": "llm",
    }
