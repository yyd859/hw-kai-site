"""Multi-turn planning loop agent."""
import json
import os

from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

# In-memory session store
# session_id -> {history: [], current_spec: {}, turn: int, awaiting_confirmation: bool}
sessions: dict[str, dict] = {}

EMPTY_SPEC = {
    "object": None,
    "trigger": None,
    "needs_light": False,
    "needs_sound": False,
    "needs_display": False,
    "needs_sensor": False,
    "sensor_type": None,
    "extra_notes": None,
}

SYSTEM_PROMPT = """你是一个硬件项目规划助手，帮助用户一步步明确他们想做的硬件项目。

你的任务：
1. 理解用户最新的输入
2. 更新对已知需求的理解（updated_spec）
3. 如果信息不足，用自然语言提出下一个关键问题（最多一个，简洁友好）
4. 如果信息已经足够形成一个可确认的方案，先给出方案摘要，等待用户确认或修改

"信息足够"的判断标准（满足以下两点即可）：
- 大概知道是什么东西（object 或 trigger 非空）
- 至少有一个功能需求为 true（needs_light / needs_sound / needs_display / needs_sensor 中至少一个）

current_spec 字段说明：
- object: 用一句话描述这个东西是什么（如"按钮控制LED"）
- trigger: 触发方式，可选值：button / auto / motion / remote / null
- needs_light: 是否需要灯光输出
- needs_sound: 是否需要声音输出
- needs_display: 是否需要显示屏
- needs_sensor: 是否需要传感器
- sensor_type: 传感器类型（如 temperature / ultrasonic / soil_moisture）
- extra_notes: 其他补充信息

你的输出必须严格是 JSON 格式（不要有任何额外文字）：
{
  "assistant_message": "给用户看的自然语言回复（中文，友好简洁）",
  "updated_spec": {
    "object": "...",
    "trigger": "...",
    "needs_light": true,
    "needs_sound": false,
    "needs_display": false,
    "needs_sensor": false,
    "sensor_type": null,
    "extra_notes": null
  },
  "options": ["可选方向A", "可选方向B"],
  "is_ready_for_final": false
}

注意：除非用户已经明确表示“确认/可以/就这样/没问题”，否则这里通常保持 is_ready_for_final=false。"""

CONFIRM_WORDS = {
    "确认", "可以", "就这样", "没问题", "好的", "好", "行", "可以了", "确认方案", "开始生成", "生成吧", "ok", "okay"
}

REVISE_HINTS = {
    "但是", "不过", "改", "修改", "不要", "换成", "改成", "再加", "还要", "希望", "最好", "另外"
}


def _get_llm_config() -> dict:
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

    return {"provider": "mock", "api_key": "", "base_url": "", "model": "mock"}


def _build_client(config: dict) -> AsyncOpenAI | None:
    if config["provider"] == "mock":
        return None
    base_url = config["base_url"]
    if config["provider"] == "deepseek" and not base_url.endswith("/v1"):
        base_url = f"{base_url}/v1"
    return AsyncOpenAI(api_key=config["api_key"], base_url=base_url)


def _normalize_trigger(text: str) -> str | None:
    msg = text.lower()
    if any(w in msg for w in ["按钮", "button", "btn"]):
        return "button"
    if any(w in msg for w in ["自动", "auto", "开机就", "一直"]):
        return "auto"
    if any(w in msg for w in ["motion", "人体", "移动", "感应"]):
        return "motion"
    if any(w in msg for w in ["遥控", "remote", "红外"]):
        return "remote"
    return None


def _contains_negative_phrase(message: str, keywords: list[str]) -> bool:
    negative_prefixes = ["不需要", "不要", "不用", "无须", "不想要", "不带"]
    return any(f"{prefix}{keyword}" in message for prefix in negative_prefixes for keyword in keywords)


def _apply_keyword_updates(message: str, spec: dict) -> dict:
    updated = dict(spec)
    msg_lower = message.lower()

    light_keywords = ["led", "灯", "light", "亮"]
    sound_keywords = ["beep", "蜂鸣", "sound", "声音", "buzzer"]
    display_keywords = ["oled", "display", "屏幕", "显示"]
    sensor_keywords = ["sensor", "传感器", "温度", "temperature", "距离", "ultrasonic", "土壤", "soil"]

    if _contains_negative_phrase(message, light_keywords):
        updated["needs_light"] = False
    elif any(w in msg_lower for w in light_keywords):
        updated["needs_light"] = True
        if not updated.get("object"):
            updated["object"] = "LED 灯光控制"

    if _contains_negative_phrase(message, sound_keywords):
        updated["needs_sound"] = False
    elif any(w in msg_lower for w in sound_keywords):
        updated["needs_sound"] = True

    if _contains_negative_phrase(message, display_keywords):
        updated["needs_display"] = False
    elif any(w in msg_lower for w in display_keywords):
        updated["needs_display"] = True

    if _contains_negative_phrase(message, sensor_keywords):
        updated["needs_sensor"] = False
        updated["sensor_type"] = None
    elif any(w in msg_lower for w in sensor_keywords):
        updated["needs_sensor"] = True
        if "温度" in msg_lower or "temperature" in msg_lower:
            updated["sensor_type"] = "temperature"
        elif "距离" in msg_lower or "ultrasonic" in msg_lower:
            updated["sensor_type"] = "ultrasonic"
        elif "土壤" in msg_lower or "soil" in msg_lower:
            updated["sensor_type"] = "soil_moisture"

    trigger = _normalize_trigger(message)
    if trigger:
        updated["trigger"] = trigger

    if not updated.get("object") and message.strip():
        updated["object"] = message.strip()[:30]

    if updated.get("extra_notes"):
        updated["extra_notes"] = f"{updated['extra_notes']}；{message[:60]}"
    elif len(message.strip()) > 12:
        updated["extra_notes"] = message.strip()[:60]

    return updated


def _mock_response(turn: int, message: str, spec: dict) -> dict:
    """Mock LLM response when no API key is available."""
    updated_spec = _apply_keyword_updates(message, spec)

    if turn == 0:
        return {
            "assistant_message": f"我理解你想做「{updated_spec.get('object', message[:20])}」，请告诉我更多细节：你更需要灯光、声音、显示，还是传感器检测？",
            "updated_spec": updated_spec,
            "options": ["只需要 LED 灯", "需要蜂鸣器声音", "需要传感器检测"],
            "is_ready_for_final": False,
        }
    if turn == 1:
        return {
            "assistant_message": "明白了。再确认一个关键点：它是按钮触发、自动运行，还是感应/遥控触发？",
            "updated_spec": updated_spec,
            "options": ["按钮触发", "自动运行", "感应/遥控触发"],
            "is_ready_for_final": False,
        }

    return {
        "assistant_message": _build_confirmation_message(updated_spec),
        "updated_spec": updated_spec,
        "options": ["确认，开始生成", "我想再改一下"],
        "is_ready_for_final": False,
    }


async def _llm_response(client: AsyncOpenAI, config: dict, history: list, spec: dict, awaiting_confirmation: bool) -> dict:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({
        "role": "system",
        "content": (
            f"当前已知的项目需求 (current_spec)：{json.dumps(spec, ensure_ascii=False)}\n"
            f"当前是否在等待用户确认：{json.dumps(awaiting_confirmation, ensure_ascii=False)}"
        ),
    })
    messages.extend(history)

    resp = await client.chat.completions.create(
        model=config["model"],
        messages=messages,
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    parsed = json.loads(raw)
    parsed.setdefault("updated_spec", spec)
    parsed.setdefault("options", [])
    parsed.setdefault("is_ready_for_final", False)
    return parsed


def _is_spec_ready(spec: dict) -> bool:
    has_object = bool(spec.get("object") or spec.get("trigger"))
    has_function = any([
        spec.get("needs_light"),
        spec.get("needs_sound"),
        spec.get("needs_display"),
        spec.get("needs_sensor"),
    ])
    return has_object and has_function


def _is_confirm_message(message: str) -> bool:
    msg = message.strip().lower()
    if not msg:
        return False
    if any(hint in msg for hint in REVISE_HINTS):
        return False
    return any(word in msg for word in CONFIRM_WORDS)


def _build_confirmation_message(spec: dict) -> str:
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
        features.append("灯光输出")
    if spec.get("needs_sound"):
        features.append("声音提示")
    if spec.get("needs_display"):
        features.append("显示屏")
    if spec.get("needs_sensor"):
        sensor = spec.get("sensor_type") or "传感器"
        features.append(f"{sensor}检测")

    feature_text = "、".join(features) if features else "基础功能"
    body = "，".join(parts) if parts else "这个硬件项目"
    return f"我目前理解的方案是：{body}，包含 {feature_text}。如果这样没问题，你回复“确认”我就进入最终生成；如果想改，我可以继续调整。"


def get_or_create_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "current_spec": dict(EMPTY_SPEC),
            "turn": 0,
            "awaiting_confirmation": False,
            "last_intent_source": "mock",
        }
    return sessions[session_id]


def _merge_spec(current_spec: dict, updated_spec: dict) -> dict:
    merged = dict(current_spec)
    for key, value in updated_spec.items():
        if value is not None:
            merged[key] = value
    return merged


async def process_message(session_id: str, message: str) -> dict:
    session = get_or_create_session(session_id)
    config = _get_llm_config()
    client = _build_client(config)
    intent_source = "mock" if config["provider"] == "mock" else "llm"

    if session.get("awaiting_confirmation") and _is_confirm_message(message):
        session["history"].append({"role": "user", "content": message})
        session["history"].append({"role": "assistant", "content": _build_confirmation_message(session["current_spec"])})
        session["turn"] += 1
        session["awaiting_confirmation"] = False
        return {
            "session_id": session_id,
            "state": "final",
            "assistant_message": f"最终确认如下：{_build_confirmation_message(session['current_spec']).replace('如果这样没问题，你回复“确认”我就进入最终生成；如果想改，我可以继续调整。', '')}",
            "current_spec": session["current_spec"],
            "is_ready_for_final": True,
            "intent_source": session.get("last_intent_source", intent_source),
        }

    session["history"].append({"role": "user", "content": message})

    if client is None:
        result = _mock_response(session["turn"], message, session["current_spec"])
        intent_source = "mock"
    else:
        try:
            result = await _llm_response(
                client,
                config,
                session["history"],
                session["current_spec"],
                session.get("awaiting_confirmation", False),
            )
        except Exception:
            result = _mock_response(session["turn"], message, session["current_spec"])
            intent_source = "mock"

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
    session["last_intent_source"] = intent_source

    return {
        "session_id": session_id,
        "state": state,
        "assistant_message": assistant_msg,
        "current_spec": session["current_spec"],
        "options": options,
        "is_ready_for_final": is_ready_for_final,
        "intent_source": intent_source,
    }
